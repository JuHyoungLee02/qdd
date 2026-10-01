"""Pure tests of the L9 v2 robot profiles in harvest.l9.robot9 (R1 Pro, G1): torso rule, width maps, camera mounts."""
import math
import os

import numpy as np
import pytest

from harvest.l9 import hcam9 as HC
from harvest.l9 import robot9 as R9


def test_v2_profiles_not_in_executor_profiles():
    assert set(R9.V2_PROFILES) == {"r1pro", "g1"} and not set(R9.V2_PROFILES) & set(R9.PROFILES)


def test_r1_torso_lean_and_surface_rule():
    q = R9.r1_torso_q(0.3, -0.2)
    assert q[0] + q[1] - q[2] == pytest.approx(R9.R1_LEAN)  # pitch axes y, y, -y: torso_link4 leans by R1_LEAN
    (j1, j2, j3, j4), err = R9.r1_torso_for_surface(0.70)
    p1, p2 = j1, j2 + j1
    z = 0.34265 + 0.4 * math.cos(p1) + 0.3 * math.cos(p2) + 0.09962 * math.cos(R9.R1_LEAN)
    assert z == pytest.approx(0.70 + R9.R1_T4_ABOVE, abs=0.01) and abs(err) < 0.01
    assert abs(0.4 * math.sin(p1) + 0.3 * math.sin(p2)) < 0.03 and j3 > -1.83
    _, err_hi = R9.r1_torso_for_surface(0.95)
    assert err_hi < -0.1  # too high a surface: the torso stays at its top


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


@pytest.mark.parametrize("name", ["r1pro", "g1"])
def test_v2_prompt_swaps_hit_the_requests(name):
    from harvest.astra_solo import prompts as V2
    from harvest.astra_solo import pt_prompts as PT
    sw = R9.prompt_swaps(name)
    for text in (V2.STATIC, PT.STATIC):
        for a, b in sw:
            assert text.count(a) == 1, a[:40]
        out = R9.swap_text(text, name)
        assert R9.V2[name]["name"].split(" (")[0].split()[-1] in out


def test_v2_init_joints_inside_limits_and_g1_band():
    j = R9.v2_init_joints("r1pro", "right", 0.75)
    assert j["torso_joint3"] < 0 and j["right_gripper_finger_joint1"] == pytest.approx(0.04995)
    assert R9.g1_surface_ok(0.70) and not R9.g1_surface_ok(0.95) and not R9.g1_surface_ok(0.40)
