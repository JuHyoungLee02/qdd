"""Camera geometry for the M1 front-end (R1): pinhole in Isaac's "world" camera convention.

Camera frame = +X forward (optical axis), +Y left, +Z up (FFW_SG2_REAL_cameras OffsetCfg convention="world").
Camera pose in the world = parent link pose x mount_transform() (the camera prim's own data.pos_w is stale in this
scene, R1 brief). Depth = renderer distance_to_image_plane, i.e. the camera-frame X of the hit point.
Pixel (col, row) is sampled at its centre u = col + 0.5, v = row + 0.5 (cx = width / 2 in the copied spec).
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np


class Intr(NamedTuple):
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int


def intr_of(spec: dict) -> Intr:
    return Intr(float(spec["fx"]), float(spec["fy"]), float(spec["cx"]), float(spec["cy"]), int(spec["width"]),
                int(spec["height"]))


def quat_to_R(q) -> np.ndarray:
    w, x, y, z = (float(v) for v in q)
    n = w * w + x * x + y * y + z * z
    s = 2.0 / n
    return np.array([[1 - s * (y * y + z * z), s * (x * y - z * w), s * (x * z + y * w)],
                     [s * (x * y + z * w), 1 - s * (x * x + z * z), s * (y * z - x * w)],
                     [s * (x * z - y * w), s * (y * z + x * w), 1 - s * (x * x + y * y)]])


def cam_pose(link_pos, link_quat_wxyz, mount) -> tuple[np.ndarray, np.ndarray]:
    """(position, rotation) of the camera in the world. mount = [tx, ty, tz, qw, qx, qy, qz] in the link frame."""
    Rl = quat_to_R(link_quat_wxyz)
    p = np.asarray(link_pos, float) + Rl @ np.asarray(mount[:3], float)
    return p, Rl @ quat_to_R(mount[3:7])


def project(P, K: Intr, p, R):
    """World points (N, 3) -> (u, v, depth) arrays (continuous pixel coordinates)."""
    Pc = (np.atleast_2d(np.asarray(P, float)) - np.asarray(p, float)) @ R  # = R^T (P - p) per row
    d = Pc[:, 0]
    return K.cx - K.fx * Pc[:, 1] / d, K.cy - K.fy * Pc[:, 2] / d, d


def backproject(mask, depth, K: Intr, p, R, dmin: float = 0.0, dmax: float = np.inf) -> np.ndarray:
    """World points (N, 3) of the masked pixels with a finite depth in (dmin, dmax]."""
    rows, cols = np.nonzero(mask)
    d = depth[rows, cols].astype(float)
    ok = np.isfinite(d) & (d > max(dmin, 0.0)) & (d <= dmax)
    rows, cols, d = rows[ok], cols[ok], d[ok]
    u, v = cols + 0.5, rows + 0.5
    Pc = np.stack([d, -(u - K.cx) * d / K.fx, -(v - K.cy) * d / K.fy], axis=1)
    return Pc @ R.T + np.asarray(p, float)


def median_centroid(points, min_pts: int = 1):
    """Per-axis median of the points, or None with fewer than min_pts points."""
    pts = np.asarray(points, float)
    if len(pts) < max(min_pts, 1):
        return None
    return np.median(pts, axis=0)


def to_table(p_world, table_top_z: float) -> np.ndarray:
    """World -> table frame (x, y unchanged = robot base x/y; z = height above the table top)."""
    p = np.asarray(p_world, float).copy()
    p[..., 2] -= table_top_z
    return p
