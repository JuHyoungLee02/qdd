"""E3-ST stereo stability metrics (pure numpy; no GPU dependencies).

centroid_3d / stability / flip_rate follow plan Task 16. The helpers below them
(disparity_to_depth, fit_plane, near/above) are used by cli_e3st.
"""
from __future__ import annotations

import numpy as np


def centroid_3d(depth: np.ndarray, mask: np.ndarray, K: np.ndarray) -> np.ndarray:
    """Per-component median of back-projected mask pixels with valid depth (camera frame, m).

    Returns NaN(3) when no mask pixel has finite positive depth.
    """
    valid = mask & np.isfinite(depth) & (depth > 0)
    v, u = np.nonzero(valid)
    if u.size == 0:
        return np.full(3, np.nan)
    z = depth[v, u]
    pix = np.stack([u, v, np.ones_like(u)], axis=0).astype(float)  # 3xN
    pts = (np.linalg.inv(K) @ pix) * z  # 3xN
    return np.median(pts, axis=1)


def stability(centroids: list[np.ndarray]) -> dict:
    """Median / p95 of Euclidean distance (mm) between consecutive centroids (NaN pairs skipped)."""
    d = [
        float(np.linalg.norm(b - a)) * 1000.0
        for a, b in zip(centroids[:-1], centroids[1:])
        if np.all(np.isfinite(a)) and np.all(np.isfinite(b))
    ]
    if not d:
        return {"median_jitter_mm": float("nan"), "p95_jitter_mm": float("nan"), "n_pairs": 0}
    return {
        "median_jitter_mm": float(np.median(d)),
        "p95_jitter_mm": float(np.percentile(d, 95)),
        "n_pairs": len(d),
    }


def flip_rate(pred_series: list) -> float:
    """Drop None (unknown) first, then fraction of consecutive pairs whose value changes."""
    vals = [p for p in pred_series if p is not None]
    if len(vals) < 2:
        return float("nan")
    flips = sum(a != b for a, b in zip(vals[:-1], vals[1:]))
    return flips / (len(vals) - 1)


# ---------------------------------------------------------------- helpers

def disparity_to_depth(disp: np.ndarray, fx: float, baseline_m: float, min_disp: float = 0.5) -> np.ndarray:
    """z = fx * B / d; disparities <= min_disp or non-finite become NaN (invalid)."""
    out = np.full(disp.shape, np.nan, dtype=np.float32)
    ok = np.isfinite(disp) & (disp > min_disp)
    out[ok] = fx * baseline_m / disp[ok]
    return out


def intrinsics_from_hfov(width: int, height: int, hfov_deg: float) -> np.ndarray:
    fx = (width / 2.0) / np.tan(np.radians(hfov_deg) / 2.0)
    return np.array([[fx, 0, width / 2.0], [0, fx, height / 2.0], [0, 0, 1.0]])


def fit_plane(points: np.ndarray, iters: int = 200, tol: float = 0.01, seed: int = 0):
    """RANSAC plane on Nx3 points. Returns (unit normal n, offset d) with n.p + d = 0,
    n oriented toward the camera (n . (0,0,-1) > 0 i.e. 'up' out of the table toward the viewer)."""
    rng = np.random.default_rng(seed)
    pts = points[np.all(np.isfinite(points), axis=1)]
    best, best_n, best_d = -1, None, None
    for _ in range(iters):
        p = pts[rng.choice(len(pts), 3, replace=False)]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        nn = np.linalg.norm(n)
        if nn < 1e-9:
            continue
        n = n / nn
        d = -n @ p[0]
        cnt = int(np.sum(np.abs(pts @ n + d) < tol))
        if cnt > best:
            best, best_n, best_d = cnt, n, d
    if best_n @ np.array([0, 0, -1.0]) < 0:
        best_n, best_d = -best_n, -best_d
    return best_n, best_d


def near_update(prev: bool | None, dist_m: float, near_in: float = 0.05, near_out: float = 0.06) -> bool:
    """Hysteresis band as in M1 registry (enter < 5 cm, exit > 6 cm)."""
    if prev:
        return dist_m <= near_out
    return dist_m < near_in


def above(ca: np.ndarray, cb: np.ndarray, b_half_extent_xy: float, up: np.ndarray) -> bool:
    """a above b: horizontal offset (w.r.t. table plane normal `up`) within b's half extent and a higher."""
    diff = ca - cb
    h = float(diff @ up)
    horiz = diff - h * up
    return bool(np.linalg.norm(horiz) <= b_half_extent_xy and h > 0)
