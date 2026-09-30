"""L9 reach / view checks for either arm on arbitrary world points (pure).

The L8-D reach probe (assets_x.reach.ReachModel, right arm, y band -0.40..-0.06) is evaluated point-wise; the left
arm uses the probe at the y-mirrored point (the robot is mirror-symmetric, harvest.l9.arm). The head-camera view
check uses the probe's head camera (default head pose; the world re-checks with the episode's head pose)."""
from __future__ import annotations

import numpy as np

from ..sim.assets_x.reach import LIFT_DEFAULT, LIFTS, OBJ_H, VIEW_MARGIN_PX, Z_NEED, ReachModel
from . import arm as A

BAND_X = (0.30, 0.68)  # probe x range (reach_l9.json: wide L9 probe merged with the L8-D gate probe)
BAND_Y = (-0.52, 0.08)  # probe y range (right arm); left = mirrored


def band(arm: str) -> tuple:
    """(x range, y range) of the arm's probed work band (world)."""
    if A.check_arm(arm) == "right":
        return BAND_X, BAND_Y
    return BAND_X, (-BAND_Y[1], -BAND_Y[0])


def reach_points(rm: ReachModel, arm: str, X, Y, top: float, z_need=Z_NEED) -> np.ndarray:
    """bool array: the arm reaches (x, y) over the truth plan's z band [top + z_need[0], top + z_need[1]]."""
    X = np.asarray(X, float).ravel()
    Y = np.asarray(Y, float).ravel() * A.side(arm)  # right-arm frame
    C = rm._col_ok(top + z_need[0], top + z_need[1])  # [y, x]
    xl, xh, xin = rm._brackets(rm.xs, X)
    yl, yh, yin = rm._brackets(rm.ys, Y)
    return C[yl, xl] & C[yl, xh] & C[yh, xl] & C[yh, xh] & xin & yin


def visible_points(rm: ReachModel, X, Y, z: float, h: float = OBJ_H, margin: float = VIEW_MARGIN_PX) -> np.ndarray:
    X, Y = np.asarray(X, float).ravel(), np.asarray(Y, float).ravel()
    if rm.cam is None:
        return np.ones(X.shape, bool)
    c = rm.cam
    R, t = np.asarray(c["R"], float), np.asarray(c["t"], float)
    ok = np.ones(X.shape, bool)
    for dz in (0.0, h):
        P = np.stack([X, Y, np.full(X.shape, z + dz)], -1) - t
        Pc = P @ R
        front = Pc[:, 2] > 1e-6
        zc = np.where(front, Pc[:, 2], 1.0)
        u = c["cx"] + c["fx"] * Pc[:, 0] / zc
        v = c["cy"] + c["fy"] * Pc[:, 1] / zc
        ok &= front & (u >= margin) & (u <= c["W"] - margin) & (v >= margin) & (v <= c["H"] - margin)
    return ok


def usable_points(rm: ReachModel, arm: str, X, Y, top: float) -> np.ndarray:
    return reach_points(rm, arm, X, Y, top) & visible_points(rm, X, Y, top)


def load_default() -> ReachModel:
    import os
    return ReachModel.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9", "reach_l9.json"))


def load_base() -> ReachModel:
    """The L8-D gate probe alone (L8S band y -0.40..-0.06)."""
    import os
    return ReachModel.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9", "reach_base.json"))


__all__ = ["BAND_X", "BAND_Y", "LIFTS", "LIFT_DEFAULT", "band", "reach_points", "visible_points", "usable_points",
           "load_default"]
