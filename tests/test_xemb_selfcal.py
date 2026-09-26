"""tools/xemb/selfcal.py (track T1, 'create the frame'): camera extrinsics (and focal) from FK 3-D gripper positions +
detected 2-D gripper points, robust to swapped-arm and wild detections; temporal jump filter for detections."""
import os
import sys

import numpy as np
import pytest

pytest.importorskip("cv2")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import geom as G  # noqa: E402
from xemb import selfcal as C  # noqa: E402

K = np.array([[367.0, 0, 336.0], [0, 367.0, 188.0], [0, 0, 1]])


def _cam():
    # camera 0.5 m behind / 0.6 m above the arm base, looking forward and down (CV axes), base x forward
    s3 = np.sqrt(3) / 2
    R_cb = np.array([[0.0, -1, 0], [-0.5, 0, -s3], [s3, 0, -0.5]])  # rows = cam x, y, z in base coords
    c = np.array([-0.1, 0.0, 0.6])
    E = np.eye(4)
    E[:3, :3] = R_cb
    E[:3, 3] = -R_cb @ c
    return E


def _data(n=400, seed=0, noise=1.5, swap=0.2, wild=0.05):
    rng = np.random.default_rng(seed)
    E = _cam()
    XL = np.c_[rng.uniform(0.3, 0.6, n), rng.uniform(0.05, 0.35, n), rng.uniform(-0.35, 0.0, n)]
    XR = XL * [1, -1, 1]
    uL = np.array([G.project(K, E, p)[0] for p in XL]) + rng.normal(0, noise, (n, 2))
    uR = np.array([G.project(K, E, p)[0] for p in XR]) + rng.normal(0, noise, (n, 2))
    s = rng.random(n) < swap  # detector pointed at the other arm
    uL2, uR2 = uL.copy(), uR.copy()
    uL2[s], uR2[s] = uR[s], uL[s]
    w = rng.random(n) < wild
    uL2[w] = rng.uniform([0, 0], [672, 376], (w.sum(), 2))
    return E, XL, XR, uL2, uR2


def test_pnp_ransac_recovers_the_camera_despite_swaps_and_wild_points():
    E, XL, XR, uL, uR = _data()
    fit = C.selfcal_two_arm(XL, XR, uL, uR, K)
    rot, dist = C.pose_error(fit["E"], E)
    assert rot < 1.0 and dist < 0.01
    assert fit["resid_median_px"] < 3.0
    assert 0.6 < fit["inlier_frac"] < 0.95  # swapped / wild points are rejected


def test_focal_search_recovers_the_focal_from_data():
    E, XL, XR, uL, uR = _data(noise=1.0, swap=0.1)
    K_wrong = K.copy()
    K_wrong[0, 0] = K_wrong[1, 1] = 300.0
    best = C.focal_search(XL, XR, uL, uR, K_wrong, scales=np.linspace(0.8, 1.5, 36))
    assert abs(best["fx"] - 367.0) / 367.0 < 0.03


def _rand_rot(rng, n):
    out = []
    for _ in range(n):
        q = rng.normal(size=4)
        out.append(G.quat_wxyz_to_mat(q))
    return np.array(out)


def test_offset_solve_recovers_camera_offset_and_focal():
    rng = np.random.default_rng(3)
    n = 500
    E = _cam()
    pL = np.c_[rng.uniform(0.3, 0.6, n), rng.uniform(0.05, 0.35, n), rng.uniform(-0.35, 0.0, n)]
    pR = pL * [1, -1, 1]
    RL, RR = _rand_rot(rng, n), _rand_rot(rng, n)
    oL, oR = np.array([0.0, 0.0, 0.07]), np.array([0.01, 0.0, 0.06])  # detector aims 6-7 cm past the EE point
    Kt = K.copy()
    Kt[0, 0] = Kt[1, 1] = 400.0
    uL = C.project_many(Kt, E, pL + np.einsum("nij,j->ni", RL, oL)) + rng.normal(0, 1.5, (n, 2))
    uR = C.project_many(Kt, E, pR + np.einsum("nij,j->ni", RR, oR)) + rng.normal(0, 1.5, (n, 2))
    s = rng.random(n) < 0.15
    uL[s], uR[s] = uR[s].copy(), uL[s].copy()
    fit = C.selfcal_offset(pL, RL, pR, RR, uL, uR, K)  # starts from the wrong focal 367
    rot, dist = C.pose_error(fit["E"], E)
    assert rot < 1.0 and dist < 0.02
    assert abs(fit["K"][0, 0] - 400.0) < 8.0
    assert np.linalg.norm(fit["o_left"] - oL) < 0.01 and np.linalg.norm(fit["o_right"] - oR) < 0.01
    assert fit["resid_median_px"] < 3.0


def test_rotation_vector_roundtrip_near_180_degrees():
    for ang in (0.1, 1.5, 3.0, np.pi - 1e-4):
        ax = np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8])
        R = C._rodrigues(ax * ang)
        assert np.allclose(C._rodrigues(C._rvec(R)), R, atol=1e-6)


def test_jump_filter_drops_isolated_spikes():
    u = np.c_[np.linspace(100, 200, 30), np.full(30, 150.0)]
    u[10] = [400, 20]
    keep = C.jump_filter(u, win=2, max_px=40)
    assert not keep[10] and keep[:10].all() and keep[11:].all()


def test_jump_filter_handles_missing():
    u = np.c_[np.linspace(100, 200, 10), np.full(10, 150.0)]
    u[3] = np.nan
    keep = C.jump_filter(u, win=2, max_px=40)
    assert not keep[3] and keep[4]


def test_pose_error_zero_for_identical():
    E = _cam()
    rot, dist = C.pose_error(E, E)
    assert rot == pytest.approx(0, abs=1e-6) and dist == pytest.approx(0, abs=1e-9)
