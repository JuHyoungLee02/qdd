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
    assert all(it["text"].startswith(s["context"]["text"] + "\n\nQuestion") for it in s["items"])
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
