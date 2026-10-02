"""tools/onboard/autotune: pure geometry + range extraction (no GPU, no cuRobo)."""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "onboard", "autotune"))
import geom as G  # noqa: E402
import ranges as RG  # noqa: E402


def test_grasp_R_top_down_yaw0_closes_along_x():
    R = G.grasp_R(0.0, 0.0, 0.0)
    assert np.allclose(R[:, 2], [0, 0, 1])  # tool z = -approach, approach straight down
    assert np.allclose(R[:, 1], [1, 0, 0])  # closing axis along world x at yaw 0
    assert np.allclose(R @ R.T, np.eye(3))


def test_grasp_R_tilt_leans_approach_towards_direction():
    R = G.grasp_R(math.radians(30), math.radians(90), 0.0)
    a = -R[:, 2]
    assert a[2] < 0 and a[0] > 0.4  # moving down and away from the robot (+x)


def test_yaw_period_from_hand_descriptor():
    par = {"tips": ["a", "b"], "opposition": [[["a"], ["b"]]]}
    g1 = {"tips": ["t", "i", "m"], "opposition": [[["t"], ["i", "m"]]]}
    assert G.yaw_period_deg(par) == 180
    assert G.yaw_period_deg(g1) == 360


def test_camera_visible_ahead_not_behind():
    cam = {"R": np.eye(3), "t": np.zeros(3), "hfov": 90.0, "width": 640, "height": 480}  # cols fwd, left, up
    P = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [1.0, 2.0, 0.0], [1.0, 0.3, -0.2]])
    assert G.visible(cam, P, margin=0.05).tolist() == [True, False, False, True]


def test_pitch_of_camera_looking_down_45():
    R = G.look_R(45.0)
    assert abs(G.cam_pitch_deg(R) - 45.0) < 1e-6


def test_lean_of_base_pitched_forward():
    T0 = np.eye(4)
    T = np.eye(4)
    T[:3, :3] = G.rot_y(0.8)  # +y rotation tips +x down = forward lean
    assert abs(G.lean_rad(T, T0) - 0.8) < 1e-9


def _synthetic():
    """2 body configs (lean 0.2 / 0.8), 3 surfaces, x 4 x y 3 points, 4 levels, 4 yaws x 1 tilt. Only the 0.8
    config at the middle surface reaches; yaw 90 never lifts; the camera only sees x >= 0.4."""
    C, S, X, Y, Hn = 2, 3, 4, 3, 4
    yaws = [0, 45, 90, 135]
    ori = [{"yaw_deg": y, "tilt_deg": 0, "tdir_deg": 0} for y in yaws]
    reach = np.zeros((C, S, X, Y, Hn, len(ori)), bool)
    reach[1, 1] = True
    reach[1, 1, :, :, 1:, 2] = False  # yaw 90: grasp only, no lift / carry level
    vis = np.zeros((C, S, X, Y, 1), bool)
    vis[:, :, 1:, :, 0] = True
    return {
        "reach": reach, "vis": vis,
        "xs": np.array([0.2, 0.3, 0.4, 0.5]), "ys": np.array([-0.3, -0.2, -0.1]),
        "levels": np.array([0.04, 0.09, 0.14, 0.19]), "surfaces": np.array([0.6, 0.7, 0.8]),
        "orients": ori, "cam_pitch": np.array([[[40.0]] * S] * C),
        "configs": [{"torso_j": 0.1}, {"torso_j": 0.5}], "lean": np.array([0.2, 0.8]),
        "mount_z": np.array([1.1, 1.2]), "mount_x": np.array([0.0, 0.05]),
    }


def test_extract_finds_band_and_bad_yaw():
    prof = RG.extract(_synthetic(), band_depth=0.2, lateral=(-0.3, -0.1), lift_ref=0.10, rel=0.7)
    assert prof["surface_z_m"] == [0.7, 0.7]
    assert prof["body"]["lean_rad"] == [0.8, 0.8]
    assert prof["body"]["joints"]["torso_j"] == [0.5, 0.5]
    assert 90 in prof["hand"]["yaw_deg_bad"] and 0 in prof["hand"]["yaw_deg_ok"]
    assert prof["body"]["mount_above_surface_m"] == [0.5, 0.5]
    assert all(c["surface_z"] == 0.7 for c in prof["cells"])
    lo, hi = prof["stance_x_m"]
    assert lo <= hi
    assert prof["lift_clear_m"][0] == 0.05 and prof["lift_clear_m"][1] >= 0.10


def test_extract_ranges_never_single_value_when_band_is_wide():
    d = _synthetic()
    d["reach"][1, 2] = d["reach"][1, 1]
    prof = RG.extract(d, band_depth=0.2, lateral=(-0.3, -0.1), lift_ref=0.10, rel=0.7)
    assert prof["surface_z_m"] == [0.7, 0.8]


def test_rot_euler_recovers_pitch():
    r, p, y = G.rot_euler(G.rot_z(0.3) @ G.rot_y(0.5))
    assert abs(r) < 1e-9 and abs(p - 0.5) < 1e-9 and abs(y - 0.3) < 1e-9


def test_hand_mask_filters_lean_and_surface_minus_joint():
    import compare as CMP
    d = _synthetic()
    m = CMP.hand_mask(d, {"lean_rad": [0.75, 0.85], "surface_z_m": [0.65, 0.85]}, n_stance=2)
    assert m.shape == (2, 3, 2)
    assert m[1, 1:].all() and not m[0].any() and not m[1, 0].any()
    m2 = CMP.hand_mask(d, {"surface_minus_joint": ["torso_j", 0.15, 0.25]}, n_stance=2)
    assert m2[1, 1].all() and int(m2.sum()) == 2  # only config 1 (j 0.5) at surface 0.7: 0.7 - 0.5 = 0.2


def test_work_mask_marks_reachable_visible_points():
    prof = RG.extract(_synthetic(), band_depth=0.2, lateral=(-0.3, -0.1), lift_ref=0.10, rel=0.7)
    wm = prof["arms"]["right"]["work_mask"]
    assert wm["xs"] == [0.2, 0.3, 0.4, 0.5] and len(wm["ok"]) == 4
    assert wm["ok"][0] == [False, False, False] and all(all(r) for r in wm["ok"][1:])


def test_camera_pitch_band_removes_cells_outside():
    prof = RG.extract(_synthetic(), band_depth=0.2, lateral=(-0.3, -0.1), lift_ref=0.10, rel=0.7,
                      cam_pitch_band=(50.0, 70.0))
    assert prof["stats"]["n_feasible"] == 0
    prof = RG.extract(_synthetic(), band_depth=0.2, lateral=(-0.3, -0.1), lift_ref=0.10, rel=0.7,
                      cam_pitch_band=(30.0, 50.0))
    assert prof["stats"]["n_feasible"] > 0 and prof["core"]["surface_z_m"] == [0.7, 0.7]


def test_compare_hand_best_stance_mean():
    import compare as CMP
    out = CMP.compare({"right": _synthetic()}, {"lean_rad": [0.75, 0.85]}, band_depth=0.2, lateral=(-0.3, -0.1))
    assert out["hand_mean_best_stance"] >= out["hand_mean"]


def test_pitch_beyond_vertical_is_not_folded():
    assert abs(G.cam_pitch_deg(G.look_R(110.0)) - 110.0) < 1e-6


def test_body_clearance_removes_stances_inside_the_body():
    d = _synthetic()
    d["body_front_x"] = np.full((2, 3), 0.25)  # body reaches x 0.25 below the surface top
    sc, st = RG.cell_scores(d, 0.2, (-0.3, -0.1), 0.10)
    ok = RG.clear_mask(d, st)  # stance d ok iff d - FURN_INSET >= body_front_x + BODY_GAP
    assert ok.shape == sc.shape
    assert not ok[:, :, [i for i, s in enumerate(st) if s < 0.25 + RG.FURN_INSET + RG.BODY_GAP - 1e-9]].any()
    prof = RG.extract(d, band_depth=0.2, lateral=(-0.3, -0.1), lift_ref=0.10, rel=0.7)
    assert all(c["stance_x"] >= 0.25 + RG.FURN_INSET + RG.BODY_GAP - 1e-9 for c in prof["cells"])


def test_cells_need_most_of_the_band_in_view():
    d = _synthetic()
    d["vis"][:, :, 1, :, 0] = False  # camera now sees only x >= 0.4 -> band starting at 0.3 is half hidden
    prof = RG.extract(d, band_depth=0.2, lateral=(-0.3, -0.1), lift_ref=0.10, rel=0.0)
    assert all(c["stance_x"] >= 0.4 - 1e-9 for c in prof["cells"])
