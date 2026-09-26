"""Behavior policy of the E-TEACH-L8 collection (prereg §3.2): what the robot EXECUTES at a call, while the label is
always the truth command for the state before it (labels.py). DART-style state mix: with probability p a
perturbation replaces the truth command, so later calls see off-path / recovery states labelled with the truth
recovery command.

Approach kinds (target not held):
  noise         truth target + N(0, 3 cm) xy, N(0, 1.5 cm) z; a truth close stays a close (-> empty closes)
  wrong_offset  target xy + 7-10 cm in a random direction (E-ACC off_a size), at the truth height
  wrong_object  above a distractor or the place object (E-ACC off_c: the wrong object)
  off_path      random point of the workspace box, 10-30 cm above the table
  empty_close   the grasp height 2-5 cm off the target, then close
  early_close   close in place
  reach_limit   the far right corner of the box, near the arm's reach (the proxy's BLOCKED point)
  clip          a point outside the workspace box (clipped, reported)
Carry kinds (target held):
  noise         truth target + N(0, 3 cm) xy, z never below table + 15 cm
  wrong_place   place xy + 7-10 cm at carry height
  off_path      random point of the box at carry height
  (clip removed from carry after the pilot: the arm flailed and dropped the mug, s20001)
  slip          open in place, only while the TCP is within 6 cm of the grasp height (grasp slip without a fall)
No perturbation at done / reopen / tipped states.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..astra_motion.executor import SAFE_X, SAFE_Y
from ..astra_motion.harness import GRASP_BELOW_TOP_M, obj_height
from . import labels as L

APPROACH_KINDS = ("noise", "wrong_offset", "wrong_object", "off_path", "empty_close", "early_close", "reach_limit",
                  "clip")
CARRY_KINDS = ("noise", "wrong_place", "off_path", "slip")  # no clip while carrying: pilot s20001 arm flail + drop
SLIP_DZ = 0.06


@dataclass
class Ctx:
    state: dict
    info: dict
    table_z: float
    step: str
    label_cmd: dict | None


def _r(p) -> list:
    return [round(float(v), 3) for v in p]


def _ring(rng, c, r0=0.07, r1=0.10):
    a = rng.uniform(0, 2 * np.pi)
    r = rng.uniform(r0, r1)
    return np.asarray(c[:2], float) + r * np.array([np.cos(a), np.sin(a)])


def allowed(c: Ctx) -> tuple:
    if c.step in ("above_target", "descend_close", "lift_clear"):
        return APPROACH_KINDS
    if c.step in L.CARRY_STEPS:
        tg = c.info["tgt"]
        gz = c.table_z + obj_height(tg) - GRASP_BELOW_TOP_M
        low = float(np.asarray(c.state["tcp"], float)[2]) <= gz + SLIP_DZ
        return CARRY_KINDS if low else tuple(k for k in CARRY_KINDS if k != "slip")
    return ()


def perturb(rng, kind: str, c: Ctx) -> dict:
    tz, tg, pl = c.table_z, c.info["tgt"], c.info["place"]
    obj = c.state["obj"]
    tcp = np.asarray(c.state["tcp"], float)
    carry = c.step in L.CARRY_STEPS
    base = np.asarray(c.label_cmd["position_m"], float) if c.label_cmd and "position_m" in c.label_cmd else tcp
    zc = tz + L.CARRY_DZ
    gz = tz + obj_height(tg) - GRASP_BELOW_TOP_M
    if kind == "noise":
        p = base + np.r_[rng.normal(0, 0.03, 2), rng.normal(0, 0.015)]
        if carry:
            p[2] = max(p[2], tz + 0.15)
        g = "keep" if carry else c.label_cmd.get("gripper", "keep")
        return {"mode": "eef", "position_m": _r(p), "gripper": g}
    if kind == "wrong_offset":
        xy = _ring(rng, obj[tg])
        return {"mode": "eef", "position_m": _r([xy[0], xy[1], base[2]]), "gripper": "keep"}
    if kind == "wrong_object":
        others = [k for k in c.info["present"] if k != tg and k in obj]
        k = others[int(rng.integers(len(others)))]
        o = np.asarray(obj[k], float)
        top = tz + (obj_height(k) if k != "o11" else 0.0)
        return {"mode": "eef", "position_m": _r([o[0], o[1], top + 0.10]), "gripper": "keep"}
    if kind == "off_path":
        z = zc + rng.uniform(-0.02, 0.06) if carry else tz + rng.uniform(0.10, 0.30)
        return {"mode": "eef", "position_m": _r([rng.uniform(*SAFE_X), rng.uniform(*SAFE_Y), z]), "gripper": "keep"}
    if kind == "empty_close":
        xy = _ring(rng, obj[tg], 0.02, 0.05)
        return {"mode": "eef", "position_m": _r([xy[0], xy[1], gz]), "gripper": "close"}
    if kind == "early_close":
        return {"mode": "gripper", "gripper": "close"}
    if kind == "reach_limit":
        return {"mode": "eef", "position_m": _r([rng.uniform(0.60, 0.65), rng.uniform(-0.50, -0.42),
                                                 tz + rng.uniform(0.18, 0.30)]), "gripper": "keep"}
    if kind == "clip":
        side = int(rng.integers(3))
        x, y = rng.uniform(*SAFE_X), rng.uniform(*SAFE_Y)
        if side == 0:
            x = SAFE_X[1] + rng.uniform(0.03, 0.12)
        elif side == 1:
            y = SAFE_Y[1] + rng.uniform(0.03, 0.12)
        else:
            y = SAFE_Y[0] - rng.uniform(0.03, 0.12)
        z = zc if carry else tz + rng.uniform(0.12, 0.30)
        return {"mode": "eef", "position_m": _r([x, y, z]), "gripper": "keep"}
    if kind == "wrong_place":
        xy = _ring(rng, obj[pl])
        return {"mode": "eef", "position_m": _r([xy[0], xy[1], zc]), "gripper": "keep"}
    if kind == "slip":
        return {"mode": "gripper", "gripper": "open"}
    raise ValueError(kind)


def choose(rng, c: Ctx, p: float):
    """-> (executed command, kind); kind 'clean' = the truth label itself."""
    kinds = allowed(c)
    if c.label_cmd is None or not kinds or rng.random() >= p:
        return c.label_cmd, "clean"
    kind = kinds[int(rng.integers(len(kinds)))]
    if kind == "wrong_object" and not [k for k in c.info["present"] if k != c.info["tgt"]]:
        kind = "wrong_offset"
    return perturb(rng, kind, c), kind
