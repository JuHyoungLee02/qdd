"""E-SR1c (prereg_sr1c): far-segment counterfactual branches -- forced decisions, forced-direction IK chunks, filters."""
import math

import numpy as np
import pytest

from harvest.train import sr1c_branch as B
from harvest.train.se2e_data import fk_ee, load_arm_chain

# ffw_bg2_rev4_follower right arm chain (= tests/train/test_se2e_data.URDF) + joint limits
URDF = """<robot name="t">
<joint name="arm_r_joint1" type="revolute"><parent link="arm_base_link"/><child link="r1"/>
  <origin xyz="0 -0.1045 0" rpy="0 0 0"/><axis xyz="0 1 0"/><limit lower="-3.14" upper="3.14"/></joint>
<joint name="arm_r_joint2" type="revolute"><parent link="r1"/><child link="r2"/>
  <origin xyz="0 -0.123 0" rpy="0 0 0"/><axis xyz="1 0 0"/><limit lower="-3.14" upper="0.0"/></joint>
<joint name="arm_r_joint3" type="revolute"><parent link="r2"/><child link="r3"/>
  <origin xyz="0 0 -0.165" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-3.14" upper="3.14"/></joint>
<joint name="arm_r_joint4" type="revolute"><parent link="r3"/><child link="r4"/>
  <origin xyz="0.041004 0 -0.135" rpy="0 0 0"/><axis xyz="0 1 0"/><limit lower="-2.9361" upper="1.0786"/></joint>
<joint name="arm_r_joint5" type="revolute"><parent link="r4"/><child link="r5"/>
  <origin xyz="-0.041004 0 -0.1489" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-3.14" upper="3.14"/></joint>
<joint name="arm_r_joint6" type="revolute"><parent link="r5"/><child link="r6"/>
  <origin xyz="0 0 -0.1041" rpy="0 0 0"/><axis xyz="0 1 0"/><limit lower="-1.57" upper="1.57"/></joint>
<joint name="arm_r_joint7" type="revolute"><parent link="r6"/><child link="r7"/>
  <origin xyz="0 0 -0.0885" rpy="0 0 0"/><axis xyz="1 0 0"/><limit lower="-1.8201" upper="1.5804"/></joint>
<joint name="end_effector_r_joint" type="fixed"><parent link="r7"/><child link="end_effector_r_link"/>
  <origin xyz="0 0 -0.215" rpy="0 0 0"/></joint>
</robot>"""
Q0 = np.array([-1.0202, -1.0888, 1.2450, -2.3886, 0.4822, 1.2357, 1.7999])  # an R2 approach snapshot (row proprio q)
Q0[6] = 1.5  # inside the joint-7 limit


def _chain():
    return load_arm_chain(URDF, "right")


def test_fk_pose_matches_fk_ee_and_jacobian_is_finite_difference():
    ch = _chain()
    p, R = B.fk_pose(ch, Q0[None])
    np.testing.assert_allclose(p[0], fk_ee(ch, Q0), atol=1e-12)
    assert np.allclose(R[0] @ R[0].T, np.eye(3), atol=1e-12)
    J = B.jacobian(ch, Q0[None])[0]
    eps = 1e-6
    for i in range(7):
        dq = np.zeros(7)
        dq[i] = eps
        p2, R2 = B.fk_pose(ch, (Q0 + dq)[None])
        np.testing.assert_allclose((p2[0] - p[0]) / eps, J[:3, i], atol=1e-5)
        w = B.rotvec(R2[0] @ R[0].T) / eps
        np.testing.assert_allclose(w, J[3:, i], atol=1e-5)


def test_direction_units_and_magnitudes():
    assert np.allclose(B.direction("plus_x", "none_z"), [1, 0, 0])
    assert np.allclose(B.direction("minus_x_plus_y", "none_z"), [-1 / math.sqrt(2), 1 / math.sqrt(2), 0])
    u = B.direction("plus_y", "up")
    assert np.allclose(u, [0, 1 / math.sqrt(2), 1 / math.sqrt(2)])
    assert np.allclose(B.direction("none_xy", "down"), [0, 0, -1])
    assert np.allclose(B.direction("none_xy", "none_z"), 0)
    assert B.MAG_M == {"tiny": 0.005, "small": 0.01, "medium": 0.02, "large": 0.04, "xlarge": 0.08}


def test_forced_decisions_exclude_the_label_and_are_seeded():
    rng = np.random.default_rng(0)
    f = B.forced_decisions("plus_x", rng, 4)
    assert len(f) == 4 and len({x["dir_xy"] for x in f}) == 4
    assert all(x["dir_xy"] != "plus_x" and x["dir_xy"] != "none_xy" for x in f)
    assert all(x["dir_z"] in ("up", "down", "none_z") and x["mag_coarse"] in B.MAG_M for x in f)
    assert f == B.forced_decisions("plus_x", np.random.default_rng(0), 4)
    g = B.forced_decisions("none_xy", np.random.default_rng(1), 4)
    assert all(x["dir_xy"] != "none_xy" for x in g)


def test_ik_chunk_moves_the_ee_straight_with_fixed_orientation():
    ch = _chain()
    lim = B.joint_limits(URDF, "right")
    disp = 0.04 * B.direction("plus_y", "up")
    Q, info = B.ik_chunk(ch, lim, Q0, disp, H=15)
    assert Q.shape == (15, 7) and np.allclose(Q[0], Q0)
    p, R = B.fk_pose(ch, Q)
    np.testing.assert_allclose(p[-1] - p[0], disp, atol=1.5e-3)
    for k in range(15):  # straight line, linear in time
        np.testing.assert_allclose(p[k] - p[0], disp * k / 14, atol=2e-3)
    assert info["pos_err_max_m"] <= 0.002 and info["rot_err_max_deg"] <= 2.0 and info["ok"]
    assert np.abs(np.diff(Q, axis=0)).max() <= B.MAX_DQ_TICK + 1e-12


def test_ik_chunk_flags_an_unreachable_step():
    ch = _chain()
    lim = B.joint_limits(URDF, "right")
    Q, info = B.ik_chunk(ch, lim, Q0, np.array([0.0, 0.0, 0.8]), H=15)  # 80 cm in 0.5 s: joint step cap
    assert not info["ok"]


def test_speed_cap():
    assert B.cap_disp(np.array([0.08, 0, 0]), H=15)[1] == 1.0
    d, f = B.cap_disp(np.array([0.2, 0, 0]), H=15)
    assert f < 1.0 and np.linalg.norm(d) == pytest.approx(B.V_CAP * 14 / 30)


def test_box_overlap_and_table_filter():
    box = {"center": np.array([0.4, -0.3, 0.05]), "half": np.array([0.03, 0.03, 0.05])}
    assert B.gripper_hits_box(np.array([0.4, -0.3, 0.13]), box)  # fingers reach 3 cm below the finger midpoint
    assert not B.gripper_hits_box(np.array([0.4, -0.3, 0.20]), box)
    assert not B.gripper_hits_box(np.array([0.55, -0.3, 0.05]), box)
    assert B.table_ok(np.array([[0, 0, 0.05], [0, 0, 0.04]]))
    assert not B.table_ok(np.array([[0, 0, 0.05], [0, 0, 0.03]]))  # 3 cm - 2.7 cm pad = 3 mm < 5 mm


def test_branch_row_fields():
    row = {"seed": 1, "kind": "P0", "k": 30, "hz": 30, "H": 15, "arm": "right", "skill_id": "pick",
           "phase_id": "approach", "proprio": {"q": list(Q0), "qd": [0.0] * 7, "tau": [0.0] * 7, "grip": [0.107, 0.0]}, "action_exec": [[0.0] * 7 + [0.107]] * 15,
           "action_script": [[0.0] * 7 + [0.107]] * 15, "valid": [1] * 15, "aux": {"reg": {}, "cls": {}},
           "task": "mug_tray", "variant": "dr", "decision": True, "verify": {"truth": {}}}
    Q = np.tile(Q0, (15, 1))
    forced = {"dir_xy": "plus_y", "dir_z": "up", "mag_coarse": "large"}
    r = B.branch_row(row, forced, Q, {"disp": [0, 0.028, 0.028]})
    assert r["committed"] == forced and r["valid"] == [1] * 15
    assert r["action_exec"] == r["action_script"] and len(r["action_exec"]) == 15
    assert all(a[7] == 0.107 for a in r["action_exec"])  # gripper target held
    assert r["aux"] == {"reg": {}, "cls": {}} and r["verify"] is None
    assert r["branch"]["src"] == {"seed": 1, "kind": "P0", "k": 30} and r["branch"]["disp"] == [0, 0.028, 0.028]
    from harvest.train.stageb_data import check_row
    check_row(r)


def test_ik_chunk_accepts_a_base_outside_the_urdf_range_but_never_moves_further_out():
    ch = _chain()
    lim = B.joint_limits(URDF, "right")
    q = Q0.copy()
    q[6] = 1.7999  # recorded R2 target above the URDF joint-7 upper limit 1.5804
    Q, info = B.ik_chunk(ch, lim, q, 0.02 * B.direction("plus_x", "none_z"), H=15)
    assert info["ok"]
    assert (Q[:, 6] <= 1.7999 + 1e-12).all()
