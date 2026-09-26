"""Quaternion helpers (w, x, y, z) for the coupling offset (rotation-vector edits)."""
from __future__ import annotations

import math

import numpy as np


def quat_from_rotvec(rv) -> np.ndarray:
    rv = np.asarray(rv, float)
    a = float(np.linalg.norm(rv))
    if a < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return np.r_[math.cos(a / 2), math.sin(a / 2) * rv / a]


def quat_mul(a, b) -> np.ndarray:
    w1, x1, y1, z1 = (float(v) for v in a)
    w2, x2, y2, z2 = (float(v) for v in b)
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])
