"""FI-DEV specification (pure, no Isaac): seeds, conditions, injection parameters, the blind planner FSM, the
phase expectation table (what the executing policy expects after each step), test-predicate truth and failure onset.

Seeds: DEV 0-29 only (calibration 0-14, evaluation 15-29, episode level). CAL 500-549, TEST 1000-1149 and
TEST-P5 1300-1329 are refused. The DEV perturbation of a seed (P0/P1/P2) is seed % 3, the same for all 9 conditions.
"""
from __future__ import annotations

import numpy as np

from ..sim.planner import CLOSE_WAIT_S, OPEN_WAIT_S, PHASE_TIMEOUT_S

DEV_SEEDS = range(0, 30)
CAL_SEEDS = range(0, 15)
EVAL_SEEDS = range(15, 30)
KINDS = ("P0", "P1", "P2")

NOMINAL = "nominal"
FAILURES = ("F1_grasp_miss", "F2_slip_lift", "F3_knock_carry", "F4_place_off", "F5_stall")
HARMLESS = ("H1_cam_shake", "H2_occlusion", "H3_self_correct")
CONDITIONS = (NOMINAL, *FAILURES, *HARMLESS)

# injection sizes (fixed before the full generation; see e_m4b_meas.md §1)
F1_OFFSET_M = 0.045  # grasp aim offset along world y (fingers close along x -> the pads miss the mug)
F2_T_AFTER_LIFT = 0.3
F2_RAMP_S = 0.3
F2_W_SLIP = 0.070  # gripper target opens to mug diameter + 6 mm while lifting
F3_T_AFTER_CARRY = 1.0
F3_V_LAT = 2.5  # m/s one-shot lateral velocity write on the mug (knock). Pilot: 1.5 no effect (seed 0), 4.0 knocked it off the table
F3_V_DOWN = 0.5
F4_OFFSET_M = 0.12  # place aim offset along world y from carry start (mug ends off the tray)
F5_OFFSET_M = 0.025  # descend aim offset along world x: one finger lands on the mug rim -> stall
H1_T_AFTER_LIFT, H1_DUR, H1_AMP, H1_HZ = 0.5, 1.5, 0.03, 3.0  # head joints sinus (rad)
H2_T_AFTER_CARRY, H2_DUR, H2_FRAC = 0.3, 1.0, 0.30  # grey box over 30 % of the head image
H3_T_AFTER_CARRY, H3_DUR, H3_OFFSET_M = 0.5, 0.5, 0.02  # small detour of the carry aim and back

WORLD = ("on_tp", "contact_tp", "lifted_t", "near_tp", "above_tp")
ROBOT = ("gripper_open", "holding_t", "lifted_holding", "contact_stall")
PREDS = WORLD + ROBOT


def check_fi_seed(seed: int) -> int:
    s = int(seed)
    if s not in DEV_SEEDS:
        raise ValueError(f"seed {s}: FI-DEV uses DEV 0-29 only (never CAL 500-549 / TEST 1000-1149 / TEST-P5)")
    return s


def seed_split(seed: int) -> str:
    return "cal" if check_fi_seed(seed) in CAL_SEEDS else "eval"


def cal_fold(seed: int):
    s = check_fi_seed(seed)
    return s // 5 if s in CAL_SEEDS else None


def seed_kind(seed: int) -> str:
    return KINDS[check_fi_seed(seed) % 3]


def _rng(seed, cond):
    return np.random.default_rng([check_fi_seed(seed), 41, CONDITIONS.index(cond)])


def inject_params(seed: int, cond: str) -> dict:
    if cond not in CONDITIONS:
        raise ValueError(cond)
    r = _rng(seed, cond)
    sg = 1.0 if r.random() < 0.5 else -1.0
    if cond == "F1_grasp_miss":
        return {"offset_xy": [0.0, sg * F1_OFFSET_M]}
    if cond == "F2_slip_lift":
        return {"t_after_lift": F2_T_AFTER_LIFT, "ramp_s": F2_RAMP_S, "w_slip": F2_W_SLIP}
    if cond == "F3_knock_carry":
        return {"t_after_carry": F3_T_AFTER_CARRY, "sign": sg, "v_lat": F3_V_LAT, "v_down": F3_V_DOWN}
    if cond == "F4_place_off":
        return {"offset_xy": [0.0, sg * F4_OFFSET_M]}
    if cond == "F5_stall":
        return {"offset_xy": [sg * F5_OFFSET_M, 0.0]}
    if cond == "H1_cam_shake":
        return {"t_after_lift": H1_T_AFTER_LIFT, "dur": H1_DUR, "amp": H1_AMP, "hz": H1_HZ}
    if cond == "H2_occlusion":
        return {"t_after_carry": H2_T_AFTER_CARRY, "dur": H2_DUR, "frac": H2_FRAC, "side": "left" if sg > 0 else "right"}
    if cond == "H3_self_correct":
        return {"t_after_carry": H3_T_AFTER_CARRY, "dur": H3_DUR, "offset_xy": [0.0, sg * H3_OFFSET_M]}
    return {}


# ------------------------------------------------------------------------------------------ blind FSM
_NEXT = {"approach": "descend", "descend": "close", "close": "lift", "lift": "carry", "carry": "place_descend",
         "place_descend": "open", "open": "retreat", "retreat": "done"}


def next_phase_blind(phase: str, s: dict) -> str:
    """The scripted policy WITHOUT its failure checks (it does not know it failed, like a policy that keeps going):
    no holding / lift-height checks, and a phase timeout moves on to the next phase instead of 'fail'."""
    if phase == "done":
        return phase
    if s["t_in_phase"] > PHASE_TIMEOUT_S[phase]:
        return _NEXT[phase]
    if phase in ("approach", "descend", "lift", "carry", "retreat"):
        return _NEXT[phase] if s["reached"] else phase
    if phase == "close":
        return "lift" if s["t_in_phase"] >= CLOSE_WAIT_S else phase
    if phase == "place_descend":
        return "open" if (s["contact_under"] or s["reached"]) else phase
    if phase == "open":
        return "retreat" if s["t_in_phase"] >= OPEN_WAIT_S else phase
    raise ValueError(phase)


# ------------------------------------------------------------------------------------------ expectations
_OPEN_HAND = (("gripper_open", True), ("holding_t", False), ("contact_stall", False))
_HOLD = (("holding_t", True), ("gripper_open", False))
EXPECT = {
    "approach": _OPEN_HAND,
    "descend": _OPEN_HAND,
    "close": (),
    "lift": _HOLD,
    "carry": _HOLD + (("lifted_holding", True), ("lifted_t", True)),
    "place_descend": _HOLD + ((("above_tp", "contact_tp"), True),),
    "open": (),
    "retreat": (("on_tp", True), ("holding_t", False)),
    "done": (("on_tp", True), ("holding_t", False)),
}


def exp_name(p) -> str:
    return "|".join(p) if isinstance(p, tuple) else p


def violations(phase: str, truth: dict) -> list:
    """Expected predicates of this phase that the given values contradict (None = unknown never contradicts).
    A tuple entry is an OR: expected True means at least one of them is True."""
    out = []
    for p, want in EXPECT.get(phase, ()):
        if isinstance(p, tuple):
            vals = [truth.get(x) for x in p]
            if any(v is None for v in vals):
                continue
            if any(vals) != want:
                out.append(exp_name(p))
        else:
            v = truth.get(p)
            if v is not None and bool(v) != want:
                out.append(p)
    return out


def onset(times, phases, truths, t_inject: float):
    """Failure onset = the first snapshot at or after the injection whose TRUTH contradicts the phase expectation."""
    for t, ph, tr in zip(times, phases, truths):
        if t >= t_inject - 1e-9 and violations(ph, tr):
            return t
    return None


# ------------------------------------------------------------------------------------------ truth
def contact_open(width: float, gripper_contacts) -> bool:
    """Open-hand collision: a finger touches an object while the gripper is open (>= GRIP_OPEN_M)."""
    from ..predicates import GRIP_OPEN_M
    return bool(width >= GRIP_OPEN_M and len(gripper_contacts) > 0)


def truth(pred: dict, contact_open: bool) -> dict:
    """The 9 test predicates from the registry predicates (harvest.predicates, privileged sim state)."""
    h, lf = pred.get("holding(o3)"), pred.get("lifted(o3)")
    return {"on_tp": pred.get("on(o3,o5)"), "contact_tp": pred.get("in_contact(o3,o5)"),
            "lifted_t": lf, "near_tp": pred.get("near(o3,o5)"), "above_tp": pred.get("above(o3,o5)"),
            "gripper_open": pred.get("gripper_open"), "holding_t": h,
            "lifted_holding": None if h is None or lf is None else bool(h and lf),
            "contact_stall": bool(contact_open)}
