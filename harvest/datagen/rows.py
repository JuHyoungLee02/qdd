"""R2 row builders (pure): R4 stage-B rows, auxiliary geometry names, §61 verification-head targets.

- aux_row: harvest.perception.aux_labels (privileged sim geometry, table frame) mapped onto the R4 names
  (stageb_data.AUX_REG / AUX_CLS) for the task's target / place; g2goal = labels_v2 Δ (remaining displacement to
  the sub-phase goal). Unknown / absent -> None (masked in training).
- truth9 / verify_prev_step: the E-M4b-meas test predicates (m4b.spec, generalized from mug/tray to the task's
  target / place) and the §61 verification-head target: at a decision frame k the head sees the observation after
  the previous decision step [k-10, k) was executed; its label is whether each `expected_after` predicate of that
  step's phase (m4b.spec.EXPECT) holds in this observation (None = unknown, never a contradiction).
- stageb_row: one R4 contract row (hz 30, H, arm right, skill / phase, proprio, action_exec = action_script
  (teacher S, no residual), valid, aux) + R2 extras (task, verify).
"""
from __future__ import annotations

import math

from ..m4b import spec as FS
from ..perception.aux_labels import aux_labels
from .timing import HZ, chunk

PICK_PHASES = ("approach", "descend", "close", "lift")


def skill_of(phase: str) -> str:
    """Scripted skill executing in an FSM phase: S1 = pick, S2 = place (snapshot.stage_of split)."""
    return "pick" if phase in PICK_PHASES else "place"


def _b(v):
    return None if v is None else int(bool(v))


def aux_row(state: dict, tgt: str, place: str, goal_delta=None) -> dict:
    a = aux_labels(state, pairs=((tgt, place),))
    reg = {n: None for n in ("g2tgt_dx", "g2tgt_dy", "g2tgt_dz", "g2tgt_dist", "g2goal_dx", "g2goal_dy", "g2goal_dz",
                             "g2goal_dist", "tgt2place_dx", "tgt2place_dy", "tgt2place_dz")}
    o = a["objects"].get(tgt)
    if o is not None:
        reg.update(g2tgt_dx=o["delta_m"][0], g2tgt_dy=o["delta_m"][1], g2tgt_dz=o["delta_m"][2], g2tgt_dist=o["dist_m"])
    if goal_delta is not None:
        d = [float(v) for v in goal_delta]
        reg.update(g2goal_dx=d[0], g2goal_dy=d[1], g2goal_dz=d[2], g2goal_dist=math.sqrt(sum(v * v for v in d)))
    pr = a["pairs"].get(f"{tgt}-{place}")
    if pr is not None:
        reg.update(tgt2place_dx=pr["delta_m"][0], tgt2place_dy=pr["delta_m"][1], tgt2place_dz=pr["delta_m"][2])
    p = a["pred"]
    cls = {"gripper_open": _b(p.get("gripper_open")), "holding_tgt": _b(p.get(f"holding({tgt})")),
           "lifted_tgt": _b(p.get(f"lifted({tgt})")), "upright_tgt": _b(p.get(f"upright({tgt})")),
           "near_tgt_place": _b(p.get(f"near({tgt},{place})")),
           "contact_tgt_place": _b(p.get(f"in_contact({tgt},{place})")), "on_tgt_place": _b(p.get(f"on({tgt},{place})"))}
    return {"reg": reg, "cls": cls}


def truth9(pred: dict, tgt: str, place: str, contact_open: bool) -> dict:
    """m4b.spec.truth for (tgt, place): the 9 test predicates (world side 5, robot side 4)."""
    h, lf = pred.get(f"holding({tgt})"), pred.get(f"lifted({tgt})")
    return {"on_tp": pred.get(f"on({tgt},{place})"), "contact_tp": pred.get(f"in_contact({tgt},{place})"),
            "lifted_t": lf, "near_tp": pred.get(f"near({tgt},{place})"), "above_tp": pred.get(f"above({tgt},{place})"),
            "gripper_open": pred.get("gripper_open"), "holding_t": h,
            "lifted_holding": None if h is None or lf is None else bool(h and lf),
            "contact_stall": bool(contact_open)}


def verify_prev_step(phase_prev: str, k0: int, truth_now: dict) -> dict:
    """§61 target for the step that started at frame k0 in phase_prev, judged on this (next) observation."""
    exp, holds = [], {}
    for p, want in FS.EXPECT.get(phase_prev, ()):
        name = FS.exp_name(p)
        exp.append([name, want])
        if isinstance(p, tuple):
            vals = [truth_now.get(x) for x in p]
            holds[name] = None if any(v is None for v in vals) else (any(vals) == want)
        else:
            v = truth_now.get(p)
            holds[name] = None if v is None else (bool(v) == want)
    return {"k0": int(k0), "phase": phase_prev, "expected_after": exp, "holds": holds,
            "violations": FS.violations(phase_prev, truth_now)}


def stageb_row(seed: int, kind: str, k: int, task: str, phase: str, proprio: dict, actions, H: int, aux: dict,
               **extra) -> dict:
    a, valid = chunk(actions, k, H)
    al = [[round(float(v), 6) for v in r] for r in a]
    row = {"seed": int(seed), "kind": kind, "k": int(k), "hz": HZ, "H": int(H), "arm": "right",
           "skill_id": skill_of(phase), "phase_id": phase, "proprio": proprio, "action_exec": al,
           "action_script": [list(r) for r in al], "valid": valid, "aux": aux, "task": task}
    row.update(extra)
    return row
