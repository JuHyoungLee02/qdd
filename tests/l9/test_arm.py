import numpy as np
import pytest

from harvest.l9 import arm as A
from harvest.sim import scene as SC


def test_mirror_is_involution_and_signs():
    q = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
    assert A.mirror_q(q) == (0.1, -0.2, -0.3, 0.4, -0.5, 0.6, -0.7)
    assert A.mirror_q(A.mirror_q(q)) == pytest.approx(q)
    assert A.INIT_R_ARM == SC.INIT_R_ARM
    assert A.INIT_L_ARM == A.mirror_q(SC.INIT_R_ARM)


def test_init_joints_right_unchanged_left_mirrored():
    assert SC.init_joints("right") == SC.INIT_JOINTS
    j = SC.init_joints("left")
    assert j["arm_r_joint1"] == 0.75 and j["arm_r_joint4"] == -2.30
    assert all(f"arm_r_joint{i}" not in j for i in (2, 3, 5, 6, 7))
    assert [j[f"arm_l_joint{i}"] for i in range(1, 8)] == list(A.INIT_L_ARM)
    assert j["head_joint1"] == SC.INIT_JOINTS["head_joint1"] and j["lift_joint"] == SC.INIT_JOINTS["lift_joint"]


def test_left_joint_limits_contain_start():
    # ffw_sg2.xml left ranges (checked 2026-09-30)
    lo = (-3.14, 0.0, -3.14, -2.9361, -3.14, -1.57, -1.5804)
    hi = (3.14, 3.14, 3.14, 1.0786, 3.14, 1.57, 1.8201)
    # joint 7: the robot USD's right range differs from the MJCF (INIT_R_ARM j7 = 1.80 is valid in the USD), so the
    # j7 mirror is checked on the pod by FK (left TCP at INIT_L_ARM = y-mirrored right TCP), not here
    assert all(a <= v <= b for a, v, b in list(zip(lo, A.INIT_L_ARM, hi))[:6])


def test_scene_left_tables():
    assert set(SC.FINGER_BODIES) == {"right", "left"}
    assert all(b.startswith("gripper_l_") for b in SC.FINGER_BODIES["left"])
    assert SC.GRIPPER_PRIM["right"] == "right_gripper"


def test_arm_helpers():
    assert A.arm_start("left") == (0.34, 0.25, 0.25) and A.arm_start("right") == A.ARM_START_R
    assert A.goal_yaw("left", np.pi / 2) == -np.pi / 2
    assert A.joint_prefix("left") == "arm_l_joint" and A.wrist_camera("left") == "cam_wrist_left"
    assert A.side("left") == -1
    with pytest.raises(ValueError):
        A.check_arm("both")


def test_left_head_inertia_matches_mjcf():
    t = A.LEFT_HEAD_INERTIA
    assert t["arm_l_link4"] == (0.00633449, 0.00629266, 0.00142827)
    assert set(t) == {f"arm_l_link{i}" for i in range(1, 8)} | {"head_link1", "head_link2"}
    assert all(len(v) == 3 and min(v) > 1e-6 for v in t.values())
