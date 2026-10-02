"""L9v2-R1 (10-03): R1 Pro scene-point reachability from its measured top-down reach band (pure numpy, no GPU).

The leaned R1 arm reaches top-down only in a narrow column ahead of torso_link4 (tools/l9/v2robot/reach_band.py,
assets9/reach_v2/r1pro_band_l080.json): a node point is usable when the grasp height (node top + GRASP_DZ) AND a
carry height (node top + CARRY_DZ) are both in the band, with the torso posture of that surface
(robot9.r1_torso_for_surface, URDF FK). The AI Worker probe (reach9) knows nothing of this (pilotR: carry / place
targets 0.37-0.41 m ahead and 0.3-0.4 m to the side had no IK at any height)."""
from __future__ import annotations

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BAND = os.path.join(HERE, "assets9", "reach_v2", "r1pro_band_l080.json")
GRASP_DZ, CARRY_DZ = 0.04, 0.15  # TCP above the node top: a low grasp and the lowest carry the executor uses
_B = {}
_T4 = {}


def band():
    if "b" not in _B:
        d = json.load(open(BAND))
        nx, ny, nz = d["shape"]
        _B["b"] = (d, np.frombuffer(d["ok"].encode(), np.uint8).reshape(nx, ny, nz) == ord("1"))
    return _B["b"]


def t4_pos(surface_z: float) -> np.ndarray:
    """torso_link4 origin in the env frame for this surface's torso posture (root at robot9.v2_root_pos)."""
    key = round(float(surface_z), 3)
    if key not in _T4:
        from . import robot9 as R9
        import sys
        sys.path.insert(0, os.path.join(HERE, "..", "..", "tools", "l9", "v2robot"))
        from urdf_fk import Urdf
        u = _B.get("u") or Urdf(R9.V2["r1pro"]["urdf"])
        _B["u"] = u
        q = dict(zip(R9.V2["r1pro"]["torso"], R9.r1_torso_for_surface(key)[0]))
        _T4[key] = u.T_root("torso_link4", q)[:3, 3] + np.asarray(R9.v2_root_pos("r1pro"), float)
    return _T4[key]


def ok_points(arm: str, P) -> np.ndarray:
    """P (N, 3) offsets from torso_link4 (world axes) -> bool (N,). Left arm = right arm mirrored in y."""
    d, ok = band()
    P = np.asarray(P, float).reshape(-1, 3).copy()
    if arm == "left":
        P[:, 1] = -P[:, 1]
    idx, inside = [], np.ones(len(P), bool)
    for k, ax in enumerate("xyz"):
        lo, hi, st = d[ax]
        i = np.round((P[:, k] - lo) / st).astype(int)
        inside &= (i >= 0) & (i < d["shape"][k])
        idx.append(np.clip(i, 0, d["shape"][k] - 1))
    return inside & ok[idx[0], idx[1], idx[2]]


def usable_mask(arm: str, surface_z: float, X, Y, top: float) -> np.ndarray:
    """scene9.usable() contract (world X, Y of node points, node top z)."""
    X, Y = np.asarray(X, float).ravel(), np.asarray(Y, float).ravel()
    t = t4_pos(surface_z)
    out = np.ones(len(X), bool)
    for dz in (GRASP_DZ, CARRY_DZ):
        P = np.stack([X - t[0], Y - t[1], np.full(len(X), float(top) + dz - t[2])], 1)
        out &= ok_points(arm, P)
    return out
