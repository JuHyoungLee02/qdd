"""MolmoAct on real data (plan 2026-09-26-molmoact-real-readiness Task 1): gripper segments, robust DLT against the
FK end effector, pointing filters, path divergence."""
import math

import numpy as np
import pytest

from harvest.train import se2e_molmo as M


def test_grip_segment_ends_release_frames():
    g = [0.0, 0.0, 0.9, 1.0, 1.0, 0.3, 0.0, 0.0, 0.8, 0.9, 0.1, 0.0]
    #    0    1    2    3    4    5*   6    7    8    9    10*  11
    ends = M.grip_segment_ends(g)
    assert ends == [5, 5, 5, 5, 5, 5, 10, 10, 10, 10, 10, None]
    assert M.grip_segment_ends([0.0, 0.0, 0.0]) == [None, None, None]  # never released
    assert M.grip_segment_ends([1.0, 1.0, 0.0]) == [2, 2, None][:2] + [2]  # closed from the start, released at 2


def _camera():
    f, cx, cy = 367.0, 336.0, 188.0
    R = np.array([[0.0, -1.0, 0.0], [-0.64, 0.0, -0.77], [0.77, 0.0, -0.64]])  # a look-forward-down camera
    t = np.array([0.0, 0.6, 0.4])
    K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1.0]])
    return K @ np.concatenate([R, t[:, None]], 1)


def _proj(P, X):
    x = np.concatenate([X, np.ones((len(X), 1))], 1) @ P.T
    return x[:, :2] / x[:, 2:3]


def test_ransac_dlt_recovers_camera_and_flags_outliers():
    rng = np.random.default_rng(0)
    P = _camera()
    X = np.stack([rng.uniform(0.3, 0.6, 200), rng.uniform(-0.3, 0.3, 200), rng.uniform(-0.3, 0.1, 200)], 1)
    uv = _proj(P, X) + rng.normal(0, 2.0, (200, 2))
    bad = rng.choice(200, 30, replace=False)
    uv[bad] += rng.uniform(60, 150, (30, 2)) * rng.choice([-1, 1], (30, 2))
    Mf, inl, res = M.ransac_dlt(X, uv, thr=15.0, iters=1000, seed=0)
    assert inl[bad].sum() == 0
    assert inl.sum() >= 165
    assert np.median(res[inl]) < 4.0
    assert np.allclose(M.dlt_project(Mf, X[:5]), _proj(P, X[:5]), atol=3.0)


def test_ransac_dlt_too_few_points():
    Mf, inl, res = M.ransac_dlt(np.zeros((4, 3)), np.zeros((4, 2)))
    assert Mf is None and not inl.any() and np.isnan(res).all()


def test_side_conflict_and_jumps():
    L = [(100.0, 100.0), (110.0, 100.0), None, (500.0, 300.0)]
    R = [(300.0, 100.0), (120.0, 105.0), (50.0, 50.0), None]
    assert M.side_conflict(L, R, 25.0) == [False, True, False, False]
    uv = [(100.0 + i, 100.0) for i in range(10)]
    uv[5] = (200.0, 100.0)
    uv[7] = None
    fl = M.jump_flags(uv, win=2, px=40.0)
    assert fl[5] is True and sum(fl) == 1


def _arm_paths(n):
    s = np.linspace(0, 1, n)
    XL = np.stack([0.35 + 0.2 * s, 0.25 - 0.1 * np.sin(3 * s), -0.2 + 0.15 * np.sin(5 * s) ** 2], 1)
    XR = np.stack([0.40 + 0.15 * np.sin(2 * s), -0.25 + 0.1 * s, -0.1 - 0.1 * np.cos(4 * s)], 1)
    return XL, XR


def test_filter_episode_reasons_and_joint_camera():
    rng = np.random.default_rng(1)
    P = _camera()
    n = 120
    XL, XR = _arm_paths(n)
    uvL = [tuple(p) for p in _proj(P, XL) + rng.normal(0, 1.5, (n, 2))]
    uvR = [tuple(p) for p in _proj(P, XR) + rng.normal(0, 1.5, (n, 2))]
    uvR[10] = None
    uvR[20] = (uvR[20][0] + 120.0, uvR[20][1])
    uvR[30] = uvL[30]  # "right" answer on the left gripper -> side conflict (both points dropped)
    kL, wL, kR, wR, info = M.filter_episode(uvL, XL, uvR, XR)
    assert wR[10] == "fail" and wR[30] == "side" and wL[30] == "side" and wR[20] in ("jump", "dlt")
    assert kR[0] and kL[0] and not kR[10] and not kR[20] and not kR[30]
    assert sum(kL) >= n - 3 and sum(kR) >= n - 5
    assert info["inlier_frac"] > 0.95 and info["median_resid_px"] < 4.0


def test_filter_episode_drops_arm_that_does_not_follow_its_end_effector():
    rng = np.random.default_rng(2)
    P = _camera()
    n = 120
    XL, XR = _arm_paths(n)
    uvL = [tuple(p) for p in _proj(P, XL) + rng.normal(0, 1.5, (n, 2))]
    junk = [tuple(p) for p in rng.uniform(0, 600, (n, 2))]
    kL, wL, kR, wR, info = M.filter_episode(uvL, XL, junk, XR)
    assert sum(kL) >= n - 5
    assert sum(kR) <= 0.1 * n and set(wR) <= {"dlt", "dlt_arm", "jump", "side"}
    kL2, wL2, kR2, wR2, info2 = M.filter_episode(junk, XL, list(reversed(junk)), XR)
    assert not any(kL2) and not any(kR2) and info2["fit"] is False


def test_path_divergence():
    a = np.array([[0.0, 0.0], [10.0, 0.0], [20.0, 0.0]])
    b = np.array([[0.0, 0.0], [10.0, 7.0], [20.0, 0.0]])
    assert M.path_divergence_px(b, a) == pytest.approx(7.0)
    assert M.path_divergence_px(a, a) == 0.0
    assert math.isnan(M.path_divergence_px(np.zeros((0, 2)), a))
