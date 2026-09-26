"""MolmoAct on real data (user-log 99, canon §89; plan docs/superpowers/plans/2026-09-26-molmoact-real-readiness.md).

MolmoAct (arXiv 2508.07917 §3.1) labels every frame by asking a pointing VLM for the robot gripper, drops failures and
builds the trace from the pointed points (no smoothing). On S-E2E (ROBOTIS AI Worker real recordings, 10 Hz) we point
with Molmo2-ER ("point to the <left|right> robot gripper") on the head frames. This module (pure numpy) holds:

  grip_segment_ends   per-frame trace end = the arm's next RELEASE (gripper joint value > 0.5 closed -> open), the M1
                      translation of MolmoAct's "episode end"; frames after the last release get no label
  ransac_dlt          robust 3x4 projective fit FK end effector (URDF, arm_base_link) -> pointed pixel, per episode
                      (the head pose differs per RB1 episode and the nominal camera failed E-MA1 G0 by ~100 px, so no
                      fixed camera is assumed; only "one camera per episode")
  filter_points       F1 no point, F2 left/right points on the same spot, F3 temporal jump, F4 off the episode's DLT
                      (proprio disagreement); thresholds fixed in the plan before measurement
  path_divergence_px  directed Hausdorff distance between two image paths
"""
from __future__ import annotations

import math

import numpy as np

GRIP_CLOSED = 0.5  # = se2e_data.GRIP_CLOSED (gripper joint value; 0 open .. ~1.1 closed)
SIDE_PX = 25.0  # F2
JUMP_WIN, JUMP_PX = 2, 40.0  # F3: deviation from the median of +-2 neighbours (0.2 s at 10 Hz)
DLT_THR_PX, DLT_ITERS = 15.0, 1000  # F4 RANSAC inlier threshold
DLT_RESID_PX = 20.0  # F4: residual to the refitted DLT
DLT_MIN_INLIER = 0.5  # F4: fewer inliers -> the episode's points of that arm are all dropped


def grip_segment_ends(g, closed_thr: float = GRIP_CLOSED) -> list:
    c = np.asarray(g, float) > closed_thr
    rel = [k for k in range(1, len(c)) if c[k - 1] and not c[k]]
    out, j = [], 0
    for t in range(len(c)):
        while j < len(rel) and rel[j] < t:
            j += 1
        out.append(rel[j] if j < len(rel) else None)
    return out


def _normalise(x):
    x = np.asarray(x, float)
    c = x.mean(0)
    s = math.sqrt(x.shape[1]) / max(float(np.sqrt(((x - c) ** 2).sum(1)).mean()), 1e-12)
    T = np.eye(x.shape[1] + 1)
    T[:-1, :-1] *= s
    T[:-1, -1] = -s * c
    return T


def dlt_fit(X, uv):
    """Normalised DLT: 3x4 M with uv ~ M [X 1] (>= 6 points)."""
    X, uv = np.asarray(X, float), np.asarray(uv, float)
    T3, T2 = _normalise(X), _normalise(uv)
    Xh = np.concatenate([X, np.ones((len(X), 1))], 1) @ T3.T
    xh = np.concatenate([uv, np.ones((len(uv), 1))], 1) @ T2.T
    A = []
    for (x, y, w), Xi in zip(xh, Xh):
        A.append(np.concatenate([np.zeros(4), -w * Xi, y * Xi]))
        A.append(np.concatenate([w * Xi, np.zeros(4), -x * Xi]))
    _, _, Vt = np.linalg.svd(np.asarray(A))
    Mn = Vt[-1].reshape(3, 4)
    return np.linalg.inv(T2) @ Mn @ T3


def dlt_project(Mf, X):
    x = np.concatenate([np.asarray(X, float), np.ones((len(X), 1))], 1) @ np.asarray(Mf).T
    return x[:, :2] / x[:, 2:3]


def ransac_dlt(X, uv, thr: float = DLT_THR_PX, iters: int = DLT_ITERS, seed: int = 0):
    """(M refitted on the inliers, inlier mask, residual px to M); (None, all False, NaN) with < 6 points."""
    X, uv = np.asarray(X, float).reshape(-1, 3), np.asarray(uv, float).reshape(-1, 2)
    n = len(X)
    if n < 6:
        return None, np.zeros(n, bool), np.full(n, np.nan)
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(iters):
        idx = rng.choice(n, 6, replace=False)
        try:
            Mf = dlt_fit(X[idx], uv[idx])
            r = np.linalg.norm(dlt_project(Mf, X) - uv, axis=1)
        except (np.linalg.LinAlgError, FloatingPointError):
            continue
        inl = np.isfinite(r) & (r < thr)
        if best is None or inl.sum() > best.sum():
            best = inl
    if best is None or best.sum() < 6:
        return None, np.zeros(n, bool), np.full(n, np.nan)
    Mf = dlt_fit(X[best], uv[best])
    r = np.linalg.norm(dlt_project(Mf, X) - uv, axis=1)
    return Mf, r < thr, r


def side_conflict(uv_a, uv_b, d: float = SIDE_PX) -> list:
    return [a is not None and b is not None and math.dist(a, b) < d for a, b in zip(uv_a, uv_b)]


def jump_flags(uv, win: int = JUMP_WIN, px: float = JUMP_PX) -> list:
    out = []
    for t, p in enumerate(uv):
        if p is None:
            out.append(False)
            continue
        nb = [uv[j] for j in range(max(0, t - win), min(len(uv), t + win + 1)) if j != t and uv[j] is not None]
        if len(nb) < 2:
            out.append(False)
            continue
        med = np.median(np.asarray(nb, float), 0)
        out.append(bool(math.dist(p, med) > px))
    return out


def _pre_filter(uv, uv_other) -> list:
    why = ["fail" if p is None else "ok" for p in uv]
    for t, s in enumerate(side_conflict(uv, uv_other)):
        if s and why[t] == "ok":
            why[t] = "side"
    for t, j in enumerate(jump_flags(uv)):
        if j and why[t] == "ok":
            why[t] = "jump"
    return why


def filter_episode(uv_l, X_l, uv_r, X_r, seed: int = 0):
    """Both arms of one episode share one head camera: F1-F3 per arm, then ONE RANSAC DLT on the remaining points of
    both arms (FK end effector -> pointed pixel) and F4 per point. An episode with no fit, or an arm with fewer than
    DLT_MIN_INLIER of its candidates on the fit, loses those points ('dlt_episode' / 'dlt_arm').
    Returns (keep_l, why_l, keep_r, why_r, info)."""
    why = {"l": _pre_filter(uv_l, uv_r), "r": _pre_filter(uv_r, uv_l)}
    pts = {"l": (uv_l, np.asarray(X_l, float)), "r": (uv_r, np.asarray(X_r, float))}
    cand = [(a, t) for a in ("l", "r") for t in range(len(why[a])) if why[a][t] == "ok"]
    X = np.asarray([pts[a][1][t] for a, t in cand], float).reshape(-1, 3)
    uv = np.asarray([pts[a][0][t] for a, t in cand], float).reshape(-1, 2)
    Mf, inl, res = ransac_dlt(X, uv, seed=seed)
    info = {"fit": Mf is not None, "n_cand": len(cand)}
    if Mf is None or inl.mean() < DLT_MIN_INLIER:
        for a, t in cand:
            why[a][t] = "dlt_episode"
        info["fit"] = False
    else:
        info.update(inlier_frac=round(float(inl.mean()), 4), median_resid_px=round(float(np.median(res[inl])), 3),
                    M=[[float(v) for v in row] for row in Mf])
        for i, (a, t) in enumerate(cand):
            if not res[i] <= DLT_RESID_PX:
                why[a][t] = "dlt"
        for a in ("l", "r"):
            idx = [i for i, (b, _) in enumerate(cand) if b == a]
            if idx and np.mean([res[i] <= DLT_RESID_PX for i in idx]) < DLT_MIN_INLIER:
                for i in idx:
                    why[a][cand[i][1]] = "dlt_arm"
    return ([w == "ok" for w in why["l"]], why["l"], [w == "ok" for w in why["r"]], why["r"], info)


def path_divergence_px(a, b) -> float:
    a, b = np.asarray(a, float).reshape(-1, 2), np.asarray(b, float).reshape(-1, 2)
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    return float(np.linalg.norm(a[:, None, :] - b[None, :, :], axis=-1).min(1).max())
