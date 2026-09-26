"""Arrival reconciliation (canon §91, user-log 101; plan 2026-09-26 Task 19, controller rulings N2 / R19).

An Astra answer judges the state at its request time t_state (about 9-10 s before it arrives) while the VLA kept
moving. On every valid delivered answer the driver compares (1) the state at t_state with the state now (runtime
phase = segment, T1 gripper state) and (2) the answer's command (edit translation / gripper, segment-plan `do`) with
what the VLA actually executed in between -- vla_motion = tip displacement since t_state MINUS the coupling offset
applied in that time (the VLA's own executed motion; the chunk-level trace is logged next to it) -- and classifies
exactly one verdict:

  done      the planned gripper action (edit gripper or plan `do`, open / close) already happened since t_state
            (reason action_done, factor 0), or the VLA already moved >= recon_done_frac of the edit translation in
            its direction (cos > adhere_cos; reason moved) -> the edit translation shrinks by the fraction done
            (factor = 1 - frac, 0 = skipped)
  changed   the runtime phase changed (segment), the T1 gripper state changed (gripper), or the answer is older than
            stale_edit_s and the valid-still conditions do not hold (stale) -> the command is dropped, the assessment
            is kept
  conflict  the VLA moved >= recon_still_m against the edit translation (cos < 0) -> the command is held (no offset)
            and the next request carries the evidence (since_last_request.previous_request.reconcile)
  valid     otherwise -> §11 rules unchanged (factor 1): reason still (tip moved < recon_still_m, same phase and
            gripper) or moving (moved, same phase and gripper, neither done nor against the edit)

Precedence (first match): action_done > segment > gripper > stale > conflict > done(moved) > valid. The stale rule
(canon §86, 15 s) is subsumed: an answer older than stale_edit_s is `changed` unless the valid-still conditions hold,
in which case it is `valid` and is applied (the world it judged is still the world now); the gate's stale drop is then
skipped for that answer (gate_answer stale_ok). The effective weight = layer weight x factor x authority a (the offset
multiplies a per tick, canon §84 supplement 8), so a = 0 applies nothing while the verdict is still logged."""
from __future__ import annotations

import numpy as np

from .twolayer import adherence_cos

VERDICTS = ("done", "valid", "changed", "conflict")
GRIP_KEYS = ("gripper_open", "holding_t")


def grip_state(t1: dict) -> dict:
    """The T1 gripper state used by the reconciliation: the known (non-None) gripper_open / holding_t values."""
    return {k: bool(t1[k]) for k in GRIP_KEYS if t1.get(k) is not None}


def grip_changed(g0: dict, g1: dict) -> bool:
    return any(k in g0 and k in g1 and g0[k] != g1[k] for k in GRIP_KEYS)


def action_done(action, g0: dict, g1: dict) -> bool:
    """close: the pads were open at t_state and are closed now; open: the reverse (T1 gripper_open)."""
    o0, o1 = g0.get("gripper_open"), g1.get("gripper_open")
    if o0 is None or o1 is None:
        return False
    return (action == "close" and o0 and not o1) or (action == "open" and not o0 and o1)


def _r(x):
    return None if x is None else round(float(x), 4)


def classify(*, command: str, edit_dp, edit_gripper, plan_do, vla_motion, phase0: str, phase1: str, grip0: dict,
             grip1: dict, age: float, p) -> dict:
    """One verdict (see the module doc). edit_dp / edit_gripper: the answer's raw edit (None without an edit);
    plan_do: the answer's segment-plan `do` (None in v1). Returns verdict, reason, factor (multiplier on the edit
    translation, 0 = command not applied) and the numbers used."""
    d = np.asarray(vla_motion, float)
    moved = float(np.linalg.norm(d))
    dp = None if edit_dp is None or command != "edit" else np.asarray(edit_dp, float)
    n_dp = 0.0 if dp is None else float(np.linalg.norm(dp))
    has_tr = n_dp >= p.small_edit_m
    cos = adherence_cos(d, dp) if has_tr else None
    frac = float(d @ dp) / (n_dp * n_dp) if has_tr else None
    seg_changed, g_changed = phase0 != phase1, grip_changed(grip0, grip1)
    still = moved < p.recon_still_m and not seg_changed and not g_changed
    stale = age > p.stale_edit_s + 1e-9
    acts = [x for x in ((edit_gripper if command == "edit" else None), plan_do) if x in ("open", "close")]
    factor = 1.0
    if any(action_done(x, grip0, grip1) for x in acts):
        verdict, reason, factor = "done", "action_done", 0.0
    elif seg_changed:
        verdict, reason, factor = "changed", "segment", 0.0
    elif g_changed:
        verdict, reason, factor = "changed", "gripper", 0.0
    elif stale and not still:
        verdict, reason, factor = "changed", "stale", 0.0
    elif has_tr and moved >= p.recon_still_m and cos is not None and cos < 0.0:
        verdict, reason, factor = "conflict", "opposite", 0.0
    elif has_tr and cos is not None and cos > p.adhere_cos and frac >= p.recon_done_frac - 1e-9:
        verdict, reason, factor = "done", "moved", max(0.0, 1.0 - frac)
    else:
        verdict, reason = "valid", ("still" if still else "moving")
    return {"verdict": verdict, "reason": reason, "factor": round(factor, 6), "moved_m": _r(moved), "cos": _r(cos),
            "frac_done": _r(frac), "stale": stale, "still": still}
