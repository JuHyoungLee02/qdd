"""Pure tests of the L9 v2 robot profiles in harvest.l9.robot9 (R1 Pro, G1): torso rule, width maps, camera mounts."""
import math
import os

import numpy as np
import pytest

from harvest.l9 import hcam9 as HC
from harvest.l9 import robot9 as R9


def test_v2_profiles_not_in_executor_profiles():
    assert set(R9.V2_PROFILES) == {"r1pro", "g1"} and not set(R9.V2_PROFILES) & set(R9.PROFILES)


def test_r1_torso_squat_keeps_torso_upright_and_lowers():
    q = R9.r1_torso_q(0.6)
    assert q[0] + q[1] - q[2] == pytest.approx(0.0)  # pitch axes y, y, -y
    hi, lo = R9.r1_theta_for_surface(1.0), R9.r1_theta_for_surface(0.7)
    assert 0.0 <= hi < lo <= 1.0
    th = R9.r1_theta_for_surface(0.75)
    shoulder = 0.34265 + 0.7 * math.cos(th) + 0.09962 + 0.303
    assert shoulder == pytest.approx(0.75 + 0.50, abs=1e-6)


def test_r1_width_map():
    j = R9.v2_width_to_joints("r1pro", "right", 0.06)
    assert set(j) == set(R9.V2["r1pro"]["arms"]["right"]["fingers"]) and all(v == pytest.approx(0.03) for v in j.values())
    assert max(R9.v2_width_to_joints("r1pro", "left", 0.5).values()) == pytest.approx(0.05)


@pytest.mark.skipif(not os.path.exists(os.path.join(os.path.dirname(R9.__file__), "assets9", "grippers", "g1_right.json")),
                    reason="G1 gripper json not built")
def test_g1_width_map_is_the_pinch_table():
    j = R9.v2_width_to_joints("g1", "right", 0.05)
    assert set(j) == set(R9.V2["g1"]["arms"]["right"]["fingers"]) and j["right_hand_thumb_0_joint"] == 0.0
    jl = R9.v2_width_to_joints("g1", "left", 0.05)
    assert jl["left_hand_index_1_joint"] == pytest.approx(-j["right_hand_index_1_joint"], abs=1e-3)


def _axes(profile, cam, parent_R):
    pos, q = R9.v2_mount(profile, cam)
    R = parent_R @ HC.quat_to_R(q)
    assert np.linalg.det(R) == pytest.approx(1.0)
    return R


def test_r1_head_looks_forward_and_down():
    R_zed = R9._rpy_R(-1.9199, 0.0, -1.5708)  # URDF zed_joint in torso_link4
    R = _axes("r1pro", "cam_head", R_zed)
    assert R[0, 0] > 0.9 and -0.40 < R[2, 0] < -0.30  # optical axis ~20 deg below horizontal, forward
    assert R[2, 2] > 0.9  # image up ~ world up


def test_g1_head_d435_pitch():
    R = _axes("g1", "cam_head", R9._rpy_R(0.0, 0.8307767239493009, 0.0))
    assert HC.pitch_pan(R)[0] == pytest.approx(47.6, abs=0.1)


def test_g1_wrist_looks_at_the_pinch():
    pos, q = R9.v2_mount("g1", "cam_wrist_right")
    f = HC.quat_to_R(q)[:, 0]
    d = np.array([0.074, 0.056, 0.014]) - np.array(pos)
    assert np.allclose(f, d / np.linalg.norm(d))
