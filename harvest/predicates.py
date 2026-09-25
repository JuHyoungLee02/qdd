"""T1 predicate calculator (M1 §4.0 registry), with hysteresis bands (M1 §4).

Coordinates: table-top frame, table surface at z = 0 (see harvest/sim/oracle_state.py).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from .config import CFG

GRIP_OPEN_M = 0.08  # [가정] RH-P12-RN 0-107.6 mm; open threshold, tune in sim
GRIP_EFFORT_MIN = 1.0  # [가정] sim joint effort units


@dataclass
class Obj:
    id: str
    pos: np.ndarray
    quat_wxyz: np.ndarray
    half_extents: np.ndarray
    occluded: bool = False
    id_uncertain: bool = False


@dataclass
class Gripper:
    width_m: float
    effort: float
    pos: np.ndarray


def _tilt_deg(q: np.ndarray) -> float:
    w, x, y, z = q
    # body z-axis in world = third column of the rotation matrix
    zx = 2 * (x * z + w * y)
    zy = 2 * (y * z - w * x)
    zz = 1 - 2 * (x * x + y * y)
    return float(np.degrees(np.arccos(np.clip(zz / np.linalg.norm([zx, zy, zz]), -1, 1))))


@dataclass
class PredicateState:
    _near: dict = field(default_factory=dict)

    def update(self, objs, grip, contacts, support):
        out: dict[str, bool | None] = {}
        unknown = {k for k, o in objs.items() if o.occluded or o.id_uncertain}
        for a, b in itertools.permutations(objs, 2):
            A, B = objs[a], objs[b]
            if a in unknown or b in unknown:
                for p in ("near", "on", "above", "in_contact"):
                    out[f"{p}({a},{b})"] = None
                continue
            d = float(np.linalg.norm(A.pos - B.pos))
            prev = self._near.get((a, b), False)
            now = d <= CFG.near_out_m if prev else d <= CFG.near_in_m  # M1 :140 enter <= 5 cm / exit > 6 cm
            self._near[(a, b)] = now
            out[f"near({a},{b})"] = now
            touching = frozenset({a, b}) in contacts
            out[f"in_contact({a},{b})"] = touching
            above_xy = abs(A.pos[0] - B.pos[0]) <= B.half_extents[0] and abs(A.pos[1] - B.pos[1]) <= B.half_extents[1]
            higher = A.pos[2] > B.pos[2]
            out[f"above({a},{b})"] = bool(above_xy and higher and not touching)
            out[f"on({a},{b})"] = bool(touching and support.get(a) == b and higher)
        for a, A in objs.items():
            if a in unknown:
                for p in ("holding", "upright", "lifted"):
                    out[f"{p}({a})"] = None
                continue
            out[f"upright({a})"] = _tilt_deg(A.quat_wxyz) <= CFG.tilt_max_deg
            gripped = frozenset({"gripper", a}) in contacts
            out[f"holding({a})"] = bool(gripped and grip.width_m < GRIP_OPEN_M and grip.effort >= GRIP_EFFORT_MIN)
            out[f"lifted({a})"] = bool(support.get(a) is None and A.pos[2] - A.half_extents[2] >= CFG.h_lift_m)
        out["gripper_open"] = grip.width_m >= GRIP_OPEN_M
        return out
