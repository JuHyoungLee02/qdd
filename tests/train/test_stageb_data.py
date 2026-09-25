"""Stage-B data contract (pure, no torch): image-only prompt state, R2 row checks, normalization, pool join."""
import copy
import json
import os

import numpy as np
import pytest

from harvest.train import stageb_data as D

TS = ('t_state: f13 (t=0.66s)  contract: c1  stage: S1 "pick up mug o3"\n'
      "robot: gripper=closed_holding(o3) arm=moving\n"
      "objects:\n  o3 mug red | on(table) | upright\n  o5 tray blue | on(table) | upright\n"
      "facts: gripper_open=no holding(o3)=yes lifted(o3)=no\n"
      "stage S1: exit=holding(o3) lifted(o3) invariants= elapsed=normal\n"
      "changes (last 3s): ")


def _row(seed=2000, kind="P0", k=21, H=15, **kw):
    r = {"seed": seed, "kind": kind, "k": k, "hz": 30, "H": H, "arm": "right", "skill_id": "pick",
         "phase_id": "carry", "proprio": {"q": [0.1] * 7, "qd": [0.0] * 7, "tau": [1.0] * 7, "grip": [0.04, 0.0]},
         "action_exec": [[0.1 * i] * 8 for i in range(H)], "action_script": [[0.1 * i] * 8 for i in range(H)],
         "valid": [1] * H, "aux": {"reg": {"g2goal_dx": 0.02, "g2goal_dz": None}, "cls": {"holding_tgt": 1}}}
    r.update(kw)
    return r


def _line(seed=2000, k=21, split="fit"):
    return {"seed": seed, "kind": "P0", "split": split, "k": k, "ds_id": "ds21", "phase": "carry", "decision": True,
            "text_state": TS, "state": {"present": ["o3", "o5"]},
            "images": {"cam_head": f"img/ep{seed}/k{k:03d}_cam_head.jpg",
                       "cam_wrist_right": f"img/ep{seed}/k{k:03d}_cam_wrist_right.jpg"},
            "oracle": {"dir_xy": "plus_y", "dir_z": "none_z", "mag_coarse": "large", "target": "o5",
                       "phase_choice": "continue", "progress": "valid_progress"}}


def _v2(seed=2000, kind="P0", k=21):
    return {"seed": seed, "kind": kind, "k": k,
            "labels_v2": {"dir_xy": "minus_y", "dir_z": "up", "mag_coarse": "small", "target": "o5",
                          "phase_choice": "next", "progress": "valid_progress"}}


def test_image_only_state_drops_geometry_and_predicates():
    s = D.image_only_state(TS)
    assert s.split("\n") == ['t_state: f13 (t=0.66s)  contract: c1  stage: S1 "pick up mug o3"',
                             "robot: gripper=closed arm=moving",
                             "stage S1: exit=holding(o3) lifted(o3) invariants= elapsed=normal"]
    for leak in ("objects", "facts", "o5", "on(table)", "holding(o3)=", "changes"):
        assert leak not in s.replace("exit=holding(o3)", "")


def test_prompt_state_modes():
    ln = _line()
    assert D.prompt_state(ln, "IMG") == D.image_only_state(TS)
    assert D.prompt_state(ln, "S0") == TS
    assert D.images_of(ln) == [["head camera:", ln["images"]["cam_head"]],
                               ["right wrist camera (active arm):", ln["images"]["cam_wrist_right"]]]
    assert D.images_of(ln, wrist=False) == [["head camera:", ln["images"]["cam_head"]]]
    both = dict(ln, images=dict(ln["images"], cam_wrist_left="l.jpg"))
    assert [lab for lab, _ in D.images_of(both, arm="both")] == [
        "head camera:", "right wrist camera (active arm):", "left wrist camera (active arm):"]
    assert D.camera_config(D.images_of(ln)) == "D27v1:head camera:|right wrist camera (active arm):"


def test_check_row_accepts_contract_and_rejects_breaks():
    D.check_row(_row())
    D.check_row(_row(valid=[1] * 11 + [0] * 4))
    bad = [dict(_row(), hz=10), _row(valid=[1] * 5 + [0] + [1] * 9), _row(valid=[0] + [1] * 14),
           _row(action_exec=[[0.0] * 7] * 15), _row(aux={"reg": {"bogus": 1.0}}),
           _row(proprio={"q": [0] * 7, "qd": [0] * 7, "tau": [0] * 7, "grip": [0.0]}),
           _row(committed={"progress": "x"})]
    for r in bad:
        with pytest.raises(ValueError):
            D.check_row(r)
    r = _row()
    del r["action_script"]
    with pytest.raises(ValueError):
        D.check_row(r)


def test_action_norm_absolute_and_residual():
    rows = [_row(action_exec=(np.random.default_rng(i).normal(0, 1, (15, 8))).tolist()) for i in range(4)]
    n = D.ActionNorm.fit(rows, "absolute")
    e = np.asarray(rows[0]["action_exec"], np.float32)
    z, sat = n.target(e, e)
    assert sat == 0.0 and np.allclose(n.action(z), e, atol=1e-5)
    r = D.ActionNorm("residual", xi=[0.1] * 8)
    s = np.zeros((15, 8), np.float32)
    e2 = s.copy()
    e2[0, 0], e2[1, 1] = 0.05, 0.3  # second exceeds xi -> clipped
    z, sat = r.target(e2, s)
    assert z[0, 0] == pytest.approx(0.5) and z[1, 1] == 1.0 and sat == pytest.approx(1 / (15 * 8))
    assert np.allclose(r.action(z, s)[0, 0], 0.05) and r.action(z, s)[1, 1] == pytest.approx(0.1)
    assert D.ActionNorm.from_json(json.loads(json.dumps(n.to_json()))).to_json() == n.to_json()


# ------------------------------------------------------------------ canon §63 (1)-(3) (R7 cycle-1 D1)
def test_grip_openness_maps_per_dataset_and_clips():
    """§63 (2): gripper value -> [0, 1] openness (1 = open), linear per dataset, clipped outside the range."""
    f = D.grip_open01
    assert f(0.107, "sim_width_m") == pytest.approx(1.0) and f(0.0, "sim_width_m") == pytest.approx(0.0)
    assert f(0.0535, "sim_width_m") == pytest.approx(0.5) and f(0.2, "sim_width_m") == 1.0
    assert f(-0.01, "sim_width_m") == 0.0
    o, c = D.GRIP_CAL["RB1"]  # S-E2E joint: 0 = open, ~1.1 = closed (dataset range calibration)
    assert o == 0.0 and 1.05 <= c <= 1.2
    assert f(0.0, "RB1") == pytest.approx(1.0) and f(c, "RB1") == pytest.approx(0.0)
    assert f(c / 2, "RB1") == pytest.approx(0.5) and f(1.34, "RB1") == 0.0 and f(-0.4, "RB1") == 1.0
    assert np.allclose(f(np.array([0.0, c]), "RB1"), [1.0, 0.0])  # vectorized
    for src, v in (("sim_width_m", 0.03), ("RB2", 0.4)):
        assert D.grip_value(f(v, src), src) == pytest.approx(v)
    assert D.grip_rate01(-0.107, "sim_width_m") == pytest.approx(-1.0)  # rates scale, never clip
    assert D.grip_rate01(1.0, "RB1") == pytest.approx(-1.0 / c)
    assert D.grip_source({"kind": "P0"}) == "sim_width_m" and D.grip_source({"kind": "SYN"}) == "sim_width_m"
    assert D.grip_source({"kind": "RB2", "fps_src": 10}) == "RB2"
    with pytest.raises(ValueError):
        D.grip_source({"kind": "RB9", "fps_src": 10})  # a real dataset without a calibration is refused


def test_make_sample_maps_the_gripper_to_openness_without_touching_the_row():
    r = _row(proprio={"q": [0.1] * 7, "qd": [0.0] * 7, "tau": [1.0] * 7, "grip": [0.0535, -0.0107]},
             action_exec=[[0.1] * 7 + [0.107]] * 15, action_script=[[0.1] * 7 + [0.3]] * 15)
    before = json.dumps(r)
    s = D.make_sample(r, None, [])
    assert json.dumps(r) == before
    assert s["grip_src"] == "sim_width_m" and s["arm"] == "right"
    assert s["proprio"]["grip"] == pytest.approx([0.5, -0.1])
    assert np.asarray(s["action_exec"])[:, 7] == pytest.approx(1.0)
    assert np.asarray(s["action_script"])[:, 7] == pytest.approx(1.0)  # 0.3 m > open width -> clipped
    assert np.asarray(s["action_exec"])[:, :7] == pytest.approx(0.1)
    se = _row(seed=3, kind="RB1", hz=10, H=5, arm="left", fps_src=10,
              proprio={"q": [0.1] * 7, "qd": [0.0] * 7, "tau": [0.0] * 7, "grip": [0.0, 0.0]},
              proprio_mask={"q": 1, "qd": 1, "tau": 0, "grip": 1},
              action_exec=[[0.1] * 7 + [1.3]] * 5, action_script=[[0.1] * 7 + [1.3]] * 5, valid=[1] * 5)
    s2 = D.make_sample(se, None, [], hz=10)
    assert s2["grip_src"] == "RB1" and s2["arm"] == "left" and s2["proprio"]["grip"][0] == pytest.approx(1.0)
    assert np.asarray(s2["action_exec"])[:, 7] == pytest.approx(0.0)
    assert s2["proprio_mask"] == {"q": 1, "qd": 1, "tau": 0, "grip": 1}


def _arm_rows(arm, loc, n=4, tau=5.0, mask=None):
    out = []
    for i in range(n):
        a = np.random.default_rng(i).normal(loc, 0.1, (15, 8))
        a[:, 7] = 0.5
        r = _row(arm=arm, action_exec=a.tolist(), action_script=a.tolist(),
                 proprio={"q": [loc] * 7, "qd": [0.0] * 7, "tau": [tau] * 7, "grip": [0.5, 0.0]})
        if mask is not None:
            r["proprio_mask"] = mask
        out.append(r)
    return out


def test_action_norm_keeps_per_arm_statistics():
    """§63 (1): normalization statistics per arm (left / right), not one pooled set."""
    n = D.ActionNorm.fit(_arm_rows("right", 1.0) + _arm_rows("left", -1.0), "absolute")
    assert n.stats("right")["mean"][0] == pytest.approx(1.0, abs=0.1)
    assert n.stats("left")["mean"][0] == pytest.approx(-1.0, abs=0.1)
    assert n.stats("left")["p_mean"][0] == pytest.approx(-1.0) and n.stats("right")["p_mean"][0] == pytest.approx(1.0)
    e = np.asarray(_arm_rows("left", -1.0)[0]["action_exec"], np.float32)
    zl, _ = n.target(e, e, arm="left")
    zr, _ = n.target(e, e, arm="right")
    assert abs(float(zl[:, 0].mean())) < 2.0 < abs(float(zr[:, 0].mean()))  # left data is typical for the left arm
    assert np.allclose(n.action(zl, arm="left"), e, atol=1e-5)
    p = {"q": [-1.0] * 7, "qd": [0.0] * 7, "tau": [5.0] * 7, "grip": [0.5, 0.0]}
    assert np.allclose(n.proprio(p, arm="left")[:7], 0.0, atol=1e-5)
    n2 = D.ActionNorm.from_json(json.loads(json.dumps(n.to_json())))
    assert n2.to_json() == n.to_json() and n2.grip_space == "open01@v1"
    # an arm never seen in training falls back to the pooled statistics
    only_r = D.ActionNorm.fit(_arm_rows("right", 1.0), "absolute")
    assert np.allclose(only_r.stats("left")["mean"], only_r.mean)
    # a checkpoint written before §63 (no "arms", no grip_space) loads and uses its single statistics set
    old = {"mode": "absolute", "mean": [0.0] * 8, "std": [1.0] * 8, "xi": [0.05] * 8,
           "p_mean": [0.0] * D.PROPRIO_DIM, "p_std": [1.0] * D.PROPRIO_DIM}
    o = D.ActionNorm.from_json(old)
    assert o.grip_space is None and np.allclose(o.stats("left")["mean"], 0.0)


def test_masked_proprio_is_left_out_of_statistics_and_input():
    """§63 (3): no torque in S-E2E -> tau masked: excluded from the statistics and zeroed in the expert input (the
    mask itself is a separate input channel, proprio_mask_vec)."""
    rows = _arm_rows("right", 1.0, tau=5.0) + _arm_rows("right", 1.0, tau=0.0,
                                                        mask={"q": 1, "qd": 1, "tau": 0, "grip": 1})
    n = D.ActionNorm.fit(rows, "absolute")
    tau = slice(14, 21)
    assert n.stats("right")["p_mean"][tau] == pytest.approx(5.0)  # the masked zeros do not pull the mean down
    p = {"q": [1.0] * 7, "qd": [0.0] * 7, "tau": [123.0] * 7, "grip": [0.5, 0.0]}
    x = n.proprio(p, arm="right", mask={"q": 1, "qd": 1, "tau": 0, "grip": 1})
    assert np.all(x[tau] == 0.0) and x.shape == (D.PROPRIO_DIM,)
    assert not np.all(n.proprio(p, arm="right")[tau] == 0.0)
    assert D.proprio_mask_vec(None).tolist() == [1.0, 1.0, 1.0, 1.0]
    assert D.proprio_mask_vec({"q": 1, "qd": 1, "tau": 0, "grip": 1}).tolist() == [1.0, 1.0, 0.0, 1.0]
    assert D.PROPRIO_IN_DIM == D.PROPRIO_DIM + len(D.PROPRIO_KEYS)
    with pytest.raises(ValueError):
        D.check_row(_row(proprio_mask={"torque": 0}))


def test_training_loader_takes_the_dataset_rate(tmp_path):
    """§62: the stage-B loader takes the dataset's hz (S-E2E 10 Hz / H 5, our pool / R2 data 30 Hz / H 15)."""
    assert D.DATA_HZ == {"pool": 30, "r2": 30, "se2e": 10}
    se = _row(seed=3, kind="RB2", hz=10, H=5, arm="right", fps_src=10, split="train", task="pick",
              label_window_s=0.3, images={"cam_head": "h.jpg", "cam_wrist_right": "r.jpg"},
              committed={"dir_xy": "plus_x", "dir_z": "up", "mag_coarse": "small"},
              action_exec=[[0.0] * 8] * 5, action_script=[[0.0] * 8] * 5, valid=[1] * 5,
              proprio_mask={"q": 1, "qd": 1, "tau": 0, "grip": 1}, aux={"reg": {}, "cls": {}})
    root = tmp_path / "conv"
    root.mkdir()
    (root / "RB2.stageb.jsonl").write_text(json.dumps(se) + "\n" + json.dumps(dict(se, split="val", k=5)) + "\n")
    ss, hz = D.load_for_training("se2e", se2e_root=str(root), se2e_kinds="RB2")
    assert hz == 10 and len(ss) == 2 and {s["H"] for s in ss} == {5} and ss[0]["grip_src"] == "RB2"
    (root / "RB2.stageb.jsonl").write_text(json.dumps(dict(se, hz=30)) + "\n")
    with pytest.raises(ValueError):
        D.load_for_training("se2e", se2e_root=str(root), se2e_kinds="RB2")  # a 30 Hz row in the 10 Hz dataset
    folder = tmp_path / "pool"
    folder.mkdir()
    (folder / "ep2000.jsonl").write_text(json.dumps(_line()) + "\n")
    (tmp_path / "pool.labels_v2.jsonl").write_text(json.dumps(_v2()) + "\n")
    (tmp_path / "pool.stageb.jsonl").write_text(json.dumps(_row()) + "\n")
    for data in ("pool", "r2"):
        ss, hz = D.load_for_training(data, pool=str(folder))
        assert hz == 30 and len(ss) == 1 and ss[0]["H"] == 15
    with pytest.raises(ValueError):
        D.load_for_training("bogus", pool=str(folder))


def test_aux_vectors_mask_null_and_missing():
    r, rm, c, cm = D.aux_vecs(_row()["aux"])
    i = D.AUX_REG.index("g2goal_dx")
    assert r[i] == pytest.approx(0.02 / D.AUX_REG_SCALE) and rm[i] == 1
    assert rm[D.AUX_REG.index("g2goal_dz")] == 0 and rm.sum() == 1
    assert c[D.AUX_CLS.index("holding_tgt")] == 1 and cm.sum() == 1


def test_vocab_and_decision_ids():
    v = D.Vocab(["dir_xy=plus_x", "dir_z=up"])
    ids = D.dec_ids({"dir_xy": "plus_x", "dir_z": "down"}, v)
    assert ids == [1, 0, 0, 0, 0] and len(ids) == len(D.QUESTIONS)
    assert D.Vocab.from_json(v.to_json()).ids == v.ids and len(v) == 3


def test_synthetic_rows_are_contract_valid_deterministic_and_consistent():
    a, b = D.synthetic_rows(12, seed=3), D.synthetic_rows(12, seed=3)
    assert json.dumps(a) == json.dumps(b)
    tr, va = D.split_samples(a)
    assert tr and va
    for s in a:
        assert {it["question"]: it["target"][0] for it in s["items"]} == s["committed"]
        assert np.asarray(s["action_exec"]).shape == (15, 8)
    assert any(0 in s["valid"] for s in a)


def test_load_stageb_joins_pool_labels_and_rows_without_oracle(tmp_path):
    folder = tmp_path / "pool"
    folder.mkdir()
    ln, ln2 = _line(), dict(_line(k=22), decision=False)
    (folder / "ep2000.jsonl").write_text(json.dumps(ln) + "\n" + json.dumps(ln2) + "\n")
    (tmp_path / "pool.labels_v2.jsonl").write_text(json.dumps(_v2()) + "\n")
    (tmp_path / "pool.stageb.jsonl").write_text(json.dumps(_row()) + "\n" + json.dumps(_row(k=22)) + "\n")
    ss = D.load_stageb(str(folder))
    assert len(ss) == 2
    s, s2 = ss
    assert s["split"] == "train" and len(s["items"]) == 5 and s2["items"] == [] and s2["split"] == "train"
    ims = [[lab, os.path.join(str(folder), p)] for lab, p in D.images_of(ln)]
    assert s["context"]["images"] == ims and [lab for lab, _ in ims] == ["head camera:",
                                                                        "right wrist camera (active arm):"]
    assert all(it["images"] == ims for it in s["items"])
    from harvest.jevcall import canonicalize
    assert s["context"]["text"] == canonicalize(D.image_only_state(TS))
    # the DecCall items end their state with the (b) line (canon §77); the expert context has no DecCall line
    assert all(it["text"].startswith(s["context"]["text"] + "\nlast_step: none\n\nQuestion") for it in s["items"])
    assert s["committed"] == {"dir_xy": "minus_y", "dir_z": "up", "mag_coarse": "small", "target": "o5",
                              "phase": "next"}
    # the pool oracle never matters
    ln_o = copy.deepcopy(ln)
    ln_o["oracle"] = {k: "zzz" for k in ln["oracle"]}
    (folder / "ep2000.jsonl").write_text(json.dumps(ln_o) + "\n" + json.dumps(ln2) + "\n")
    assert json.dumps(D.load_stageb(str(folder))) == json.dumps(ss)
    # S1-style ablation keeps the full text state
    s0 = D.load_stageb(str(folder), state="S0")[0]
    assert s0["context"]["text"] == canonicalize(TS)


def test_committed_row_field_overrides_label_default(tmp_path):
    folder = tmp_path / "pool"
    folder.mkdir()
    (folder / "ep2000.jsonl").write_text(json.dumps(_line()) + "\n")
    (tmp_path / "pool.labels_v2.jsonl").write_text(json.dumps(_v2()) + "\n")
    (tmp_path / "pool.stageb.jsonl").write_text(json.dumps(_row(committed={"dir_xy": "plus_x"})) + "\n")
    s = D.load_stageb(str(folder))[0]
    assert s["committed"]["dir_xy"] == "plus_x" and s["committed"]["dir_z"] == "up"
