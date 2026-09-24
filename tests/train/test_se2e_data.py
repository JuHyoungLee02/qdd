"""S-E2E real-robot data (ROBOTIS AI Worker, LeRobot v2.1) -> stage-B rows: pure conversion functions."""
import math

import numpy as np
import pytest

from harvest.train import se2e_data as S
from harvest.train import stageb_data as D

# the arm chain of ffw_bg2_rev4_follower.urdf (ROBOTIS-GIT/ai_worker 897ef34), right arm + one left joint
URDF = """<robot name="t">
<joint name="arm_r_joint1" type="revolute"><parent link="arm_base_link"/><child link="r1"/>
  <origin xyz="0 -0.1045 0" rpy="0 0 0"/><axis xyz="0 1 0"/></joint>
<joint name="arm_r_joint2" type="revolute"><parent link="r1"/><child link="r2"/>
  <origin xyz="0 -0.123 0" rpy="0 0 0"/><axis xyz="1 0 0"/></joint>
<joint name="arm_r_joint3" type="revolute"><parent link="r2"/><child link="r3"/>
  <origin xyz="0 0 -0.165" rpy="0 0 0"/><axis xyz="0 0 1"/></joint>
<joint name="arm_r_joint4" type="revolute"><parent link="r3"/><child link="r4"/>
  <origin xyz="0.041004 0 -0.135" rpy="0 0 0"/><axis xyz="0 1 0"/></joint>
<joint name="arm_r_joint5" type="revolute"><parent link="r4"/><child link="r5"/>
  <origin xyz="-0.041004 0 -0.1489" rpy="0 0 0"/><axis xyz="0 0 1"/></joint>
<joint name="arm_r_joint6" type="revolute"><parent link="r5"/><child link="r6"/>
  <origin xyz="0 0 -0.1041" rpy="0 0 0"/><axis xyz="0 1 0"/></joint>
<joint name="arm_r_joint7" type="revolute"><parent link="r6"/><child link="r7"/>
  <origin xyz="0 0 -0.0885" rpy="0 0 0"/><axis xyz="1 0 0"/></joint>
<joint name="end_effector_r_joint" type="fixed"><parent link="r7"/><child link="end_effector_r_link"/>
  <origin xyz="0 0 -0.215" rpy="0 0 0"/></joint>
<joint name="gripper_r_joint" type="fixed"><parent link="r7"/><child link="g"/>
  <origin xyz="0 0 -0.078" rpy="0 3.14159265359 3.14159265359"/></joint>
</robot>"""
DOWN = 0.165 + 0.135 + 0.1489 + 0.1041 + 0.0885 + 0.215  # arm length below joint 2 at q = 0


def _chain():
    return S.load_arm_chain(URDF, "right")


def test_fk_zero_and_joint1_rotation():
    ch = _chain()
    np.testing.assert_allclose(S.fk_ee(ch, np.zeros(7)), [0.0, -0.2275, -DOWN], atol=1e-9)
    # joint 1 turns about +y: +90 deg swings the hanging arm to -x (R_y(90) (0,0,-L) = (-L,0,0))
    q = np.zeros(7)
    q[0] = math.pi / 2
    np.testing.assert_allclose(S.fk_ee(ch, q), [-DOWN, -0.2275, 0.0], atol=1e-9)
    # batched input
    assert S.fk_ee(ch, np.zeros((5, 7))).shape == (5, 3)


def test_fk_rejects_missing_link():
    with pytest.raises(ValueError):
        S.load_arm_chain(URDF, "left")


def test_resample_chunk_linear_and_padding():
    a = np.arange(10, dtype=float)[:, None] * np.array([[1.0, 10.0]])  # 10 frames at 10 Hz
    ch, valid = S.resample_chunk(a, src_hz=10, t0_index=2, dst_hz=30, H=6)
    np.testing.assert_allclose(ch[:, 0], [2, 2 + 1 / 3, 2 + 2 / 3, 3, 3 + 1 / 3, 3 + 2 / 3])
    np.testing.assert_allclose(ch[:, 1], ch[:, 0] * 10)
    assert valid.tolist() == [1] * 6
    ch, valid = S.resample_chunk(a, 10, 8, 30, 6)  # t = 8.0 .. 9.67 frames; last sample is frame 9
    assert valid.tolist() == [1, 1, 1, 1, 0, 0]
    np.testing.assert_allclose(ch[3:, 0], [9, 9, 9])  # held at the last value
    ch, valid = S.resample_chunk(a, 10, 3, 10, 3)  # native rate
    np.testing.assert_allclose(ch[:, 0], [3, 4, 5])


def test_interp_at_and_velocity():
    x = np.array([[0.0], [1.0], [4.0], [9.0]])
    np.testing.assert_allclose(S.interp_at(x, 1.5), [2.5])
    np.testing.assert_allclose(S.interp_at(x, 7.0), [9.0])  # clamped
    v = S.finite_velocity(x, hz=10)
    np.testing.assert_allclose(v[:, 0], [10.0, 20.0, 40.0, 50.0])  # one-sided ends, central inside


def test_decision_labels_bins_and_deadband():
    lab = S.decision_labels([0.02, 0.0, -0.005])
    assert lab == {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "medium"}
    lab = S.decision_labels([-0.012, 0.03, 0.05])
    assert lab == {"dir_xy": "minus_x_plus_y", "dir_z": "up", "mag_coarse": "xlarge"}
    assert S.decision_labels([0.0, 0.0, 0.0])["mag_coarse"] == "tiny"


def test_active_arm():
    t = np.linspace(0, 1, 11)[:, None]
    still = np.zeros((11, 3))
    move = np.hstack([t * 0.1, 0 * t, 0 * t])
    assert S.active_arm(still, move) == ("right", False)
    assert S.active_arm(move, still) == ("left", False)
    assert S.active_arm(move, move * 0.8) == ("left", True)
    assert S.active_arm(still, still) == ("right", False)  # default when nothing moves


def _episode(T=40, D=16):
    rng = np.random.default_rng(0)
    st = np.cumsum(rng.normal(0, 0.01, (T, D)), 0)
    return st, st + 0.005


def test_episode_rows_meet_stageb_contract():
    st, act = _episode()
    rows = S.episode_rows(st, act, fps=10, chain={"right": _chain(), "left": _chain()}, seed=7, kind="RB2",
                          task="pick the order items", stride=5, labels=True)
    assert [r["k"] for r in rows] == [0, 5, 10, 15, 20, 25, 30, 35]
    for r in rows:
        D.check_row(r, hz=10)  # §62: S-E2E stays at the native 10 Hz
        assert r["hz"] == 10 and r["H"] == 5 and r["arm"] in ("left", "right")  # 0.5 s chunk = 5 steps
        assert r["label_steps"] == 3  # 0.33 s -> nearest step count at 10 Hz
        assert set(r["committed"]) == {"dir_xy", "dir_z", "mag_coarse"}
        assert r["labels_src"] == S.LABEL_SRC
        assert len(r["action_full"]) == 5 and len(r["action_full"][0]) == 16
        assert r["proprio_mask"]["tau"] == 0
        np.testing.assert_allclose(r["action_full"][0], act[r["k"]])  # no resampling: chunk = recorded actions
    with pytest.raises(ValueError):
        D.check_row(rows[0])  # the default (our 30 Hz data) still refuses a 10 Hz row
    assert rows[-1]["valid"] == [1, 1, 1, 1, 1] and rows[-1]["k"] == 35
    last = S.episode_rows(st, act, 10, {"right": _chain(), "left": _chain()}, 7, "RB2", "x", stride=37)[-1]
    assert last["k"] == 37 and last["valid"] == [1, 1, 1, 0, 0]  # the chunk runs past the episode end
    off = S.episode_rows(st, act, 10, {"right": _chain(), "left": _chain()}, 7, "RB2", "x", stride=5,
                         labels=False)
    assert all("committed" not in r for r in off)


def test_arm_slices_and_action_dims():
    names = S.ARM_NAMES["right"] + S.ARM_NAMES["left"]
    assert len(S.arm_index(S.FEATURE_NAMES_19, "right")) == 8
    assert S.arm_index(S.FEATURE_NAMES_19, "left") == list(range(8))
    assert S.arm_index(S.FEATURE_NAMES_19, "right") == list(range(8, 16))
    assert len(set(names)) == 16


def test_split_is_deterministic_and_stratified():
    sp = [S.split_of("RB1", i) for i in range(2000)]
    assert sp == [S.split_of("RB1", i) for i in range(2000)]
    frac = sp.count("val") / len(sp)
    assert 0.03 < frac < 0.08


def test_items_for_committed_use_option_names():
    items = S.decision_items({"dir_xy": "plus_x", "dir_z": "up", "mag_coarse": "small"}, "ctx", "train", "RB2_ep1_k0",
                             window_s=0.3)
    assert [it["question"] for it in items] == ["dir_xy", "dir_z", "mag_coarse"]
    for it in items:
        # same option lists as the DecCall (NONE_ESCALATE shown, never a heuristic target)
        assert it["target"][0] in it["names"] and it["names"][-1] == "NONE_ESCALATE"
        assert it["target"] != ["NONE_ESCALATE"] and it["source"] == S.LABEL_SRC
        assert it["text"].startswith("ctx\n\nQuestion (se2e.")


def test_load_se2e_samples_and_actions_only(tmp_path):
    import json
    st, act = _episode()
    rows = S.episode_rows(st, act, 10, {"right": _chain(), "left": _chain()}, 3, "RB1", "sort the coffee", stride=10,
                          image_ref=lambda k: {"cam_head": f"img/k{k}_h.jpg", "cam_wrist_left": f"img/k{k}_l.jpg",
                                               "cam_wrist_right": f"img/k{k}_r.jpg"})
    p = tmp_path / "RB1.stageb.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    smp = S.load_se2e(str(p), image_root="/root")
    assert len(smp) == len(rows)
    s = smp[0]
    assert s["context"]["text"].startswith('task: "sort the coffee"')
    labs = [lab for lab, _ in s["context"]["images"]]
    assert labs[0] == "head camera:" and labs[1].startswith(rows[0]["arm"])
    assert len(s["items"]) == 3 and s["items"][0]["images"] == s["context"]["images"]
    assert s["committed"] == rows[0]["committed"]
    off = S.load_se2e(str(p), labels=False)
    assert all(x["items"] == [] and x["committed"] == {} for x in off)


def test_load_se2e_skips_rows_without_needed_cameras(tmp_path):
    import json
    st, act = _episode()
    rows = S.episode_rows(st, act, 10, {"right": _chain(), "left": _chain()}, 3, "RB2", "x", stride=10,
                          image_ref=lambda k: {"cam_head": f"img/k{k}_h.jpg"})  # head-only episode
    p = tmp_path / "RB2.stageb.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert S.load_se2e(str(p)) == []
    head_only = S.load_se2e(str(p), wrist=False)
    assert len(head_only) == len(rows) and all(len(s["context"]["images"]) == 1 for s in head_only)
