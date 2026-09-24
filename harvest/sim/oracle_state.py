"""Simulator ground truth → predicate inputs (harvest.predicates).

Frame convention: table-top frame, table surface at z = 0 (x, y unchanged from the world frame).
Isaac-dependent functions import Isaac lazily so this module loads without Isaac.
"""
import numpy as np


def to_table_frame(p_world: np.ndarray, table_top_z: float) -> np.ndarray:
    p = np.asarray(p_world, dtype=float).copy()
    p[2] -= table_top_z
    return p
