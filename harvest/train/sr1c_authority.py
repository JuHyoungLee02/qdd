"""E-SR1c distance-based authority a in [0, 1] (docs/stage3/prereg_sr1c.md; research doc
docs/research/decision_adherence_0p8_2026-09-26.md §1.5; user-log 93). a = the share of an EXTERNAL decision
(joystick / Astra edit) over the chunk; the VLA's own decision is followed everywhere (user-log 94).

  a = 0   contact phase (descend, close, place_descend, open) or near contact (canon §7 runtime.core.near_contact:
          the phase target within NEAR_M = 5 cm of the gripper finger midpoint, or the held target in contact with
          the place object)
  a = 1   stage-target distance >= FAR_M = 10 cm
  linear  in between: (d - NEAR_M) / (FAR_M - NEAR_M)   [assumption; the boundary values are not tuned here]
Stage-target distance: pick phases (approach, descend, close, lift) = gripper -> target (g2tgt_dist); later phases =
gripper -> place = g2tgt (tgt - g) - tgt2place (tgt - place) (= sr1b.near_snap).
privileged(): from a stage-B row's aux (sim truth, used for strata and branch eligibility); estimated(): from the fused
model's aux-head outputs (runtime path, no new sensor). Hysteresis: the runtime / coupling-layer form (enter 5 cm,
leave 6 cm = CFG.near_in_m / near_out_m; decreases immediate, increases rate-limited to +0.5 per 0.33 s).
"""
from __future__ import annotations

import math

import numpy as np

NEAR_M = 0.05       # = config.CFG.near_in_m (test)
NEAR_OUT_M = 0.06   # = config.CFG.near_out_m (test)
FAR_M = 0.10
PICK_PHASES = ("approach", "descend", "close", "lift")  # = datagen.rows.PICK_PHASES (test)
CONTACT_PHASES = ("descend", "close", "place_descend", "open")
RATE_PER_S = 0.5 / 0.33
AUX_REG_SCALE = 0.05  # = stageb_data.AUX_REG_SCALE
AUX_REG = ("g2tgt_dx", "g2tgt_dy", "g2tgt_dz", "g2tgt_dist", "g2goal_dx", "g2goal_dy", "g2goal_dz", "g2goal_dist",
           "tgt2place_dx", "tgt2place_dy", "tgt2place_dz")  # = stageb_data.AUX_REG
AUX_CLS = ("gripper_open", "holding_tgt", "lifted_tgt", "upright_tgt", "near_tgt_place", "contact_tgt_place",
           "on_tgt_place")  # = stageb_data.AUX_CLS


def ramp(d: float) -> float:
    return float(min(1.0, max(0.0, (d - NEAR_M) / (FAR_M - NEAR_M))))


def authority(d, phase: str, contact: bool = False):
    """a from a stage distance d (m); None if d is None and the phase does not decide it."""
    if phase in CONTACT_PHASES or contact:
        return 0.0
    if d is None:
        return None
    return 0.0 if d <= NEAR_M else ramp(d)


def _place_vec(g, p):
    return np.asarray(g, float) - np.asarray(p, float)


def stage_distance(aux: dict, phase: str):
    """(distance m, contact flag) from a row's privileged aux; (None, None) when the values are missing."""
    reg, cls = (aux or {}).get("reg") or {}, (aux or {}).get("cls") or {}
    if phase in PICK_PHASES:
        d = reg.get("g2tgt_dist")
        return (None, None) if d is None else (float(d), False)
    g = [reg.get(k) for k in ("g2tgt_dx", "g2tgt_dy", "g2tgt_dz")]
    p = [reg.get(k) for k in ("tgt2place_dx", "tgt2place_dy", "tgt2place_dz")]
    if None in g or None in p:
        return None, None
    return float(np.linalg.norm(_place_vec(g, p))), cls.get("contact_tgt_place") == 1


def privileged(aux: dict, phase: str):
    d, c = stage_distance(aux, phase)
    if phase in CONTACT_PHASES:
        return 0.0
    return None if d is None else authority(d, phase, bool(c))


def estimated_distance(reg, cls_logits, phase: str):
    """(distance m, contact flag) from the aux head's outputs: reg = AUX_REG values / AUX_REG_SCALE, cls = logits."""
    r = {n: float(v) * AUX_REG_SCALE for n, v in zip(AUX_REG, np.asarray(reg, float))}
    if phase in PICK_PHASES:
        return r["g2tgt_dist"], False
    lc = float(np.asarray(cls_logits, float)[AUX_CLS.index("contact_tgt_place")])
    g = [r[k] for k in ("g2tgt_dx", "g2tgt_dy", "g2tgt_dz")]
    p = [r[k] for k in ("tgt2place_dx", "tgt2place_dy", "tgt2place_dz")]
    return float(np.linalg.norm(_place_vec(g, p))), lc > 0.0


def estimated(reg, cls_logits, phase: str) -> float:
    d, c = estimated_distance(reg, cls_logits, phase)
    return authority(d, phase, c)


def stratum(a) -> str:
    if a is None or (isinstance(a, float) and math.isnan(a)):
        return "unknown"
    return "far" if a >= 1.0 else ("near" if a <= 0.0 else "band")


class Hysteresis:
    """Runtime authority (coupling layer): near zone entered at <= NEAR_M, left only at > NEAR_OUT_M; contact phase
    -> 0; decreases immediate, increases at most RATE_PER_S * dt per step; unknown distance -> 0. Starts at 0."""

    def __init__(self, dt: float = 0.33):
        self.dt, self.a, self.near = dt, 0.0, False

    def step(self, d, phase: str, contact: bool = False) -> float:
        if d is None or phase in CONTACT_PHASES or contact:
            self.near = True
            self.a = 0.0
            return self.a
        if self.near:
            self.near = d <= NEAR_OUT_M
        else:
            self.near = d <= NEAR_M
        tgt = 0.0 if self.near else ramp(d)
        self.a = tgt if tgt <= self.a else min(tgt, self.a + RATE_PER_S * self.dt)
        return self.a
