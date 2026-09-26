"""Truth labels in the astra-solo@v2 answer schema (E-TEACH-L8, docs/stage3/prereg_teach_l8.md §3).

command: the truth plan of harvest/astra_solo/truth.py (= harvest/astra_motion/truth.py remaining_points: 10 cm above
the grasp point -> grasp point (target top - 1.8 cm) + close -> carry height table + 22 cm -> above the place ->
place height + open -> stop), with three recovery rules the clean truth never needed (its episodes never leave the
path; the perturbed collection does):
  reopen      the gripper is closed but holds nothing (empty close / slip) -> {"mode": "gripper", "gripper": "open"}
              (the clean truth would treat any closed gripper as carrying and bring nothing to the tray);
  lift_clear  the TCP is low (below target top + 3 cm) and not over the target -> straight up to the approach height
              first (the prompt's "lift before moving sideways over objects");
  retreat     after the release, the TCP still low over the object -> up 10 cm, then stop (the prompt's rule;
              pilot: bottle_tray ended in stop without success without it);
  tipped      the target is not upright and not held -> no label (the sample is dropped, the episode ends).
Stuck states (last move BLOCKED and the truth would resend the same target) are dropped (stuck()).
assessment / reason: templated from the simulator state and the measured history only (pad gap, TCP, last result) --
never a claim the two images and the text cannot support (prereg §3.3). The fixed fields: evidence_view "both",
confidence "high".
Pure (no Isaac): state = world.status() dict {tcp, grip_w, pred, obj}.
"""
from __future__ import annotations

import json

import numpy as np

from ..astra_motion.harness import GRASP_BELOW_TOP_M, obj_height
from ..astra_motion.prompts import OBJ_NAME

ABOVE_DZ = 0.10
CARRY_DZ = 0.22  # = astra_motion.truth.CARRY_DZ
NEAR_XY = 0.015
LOW_MARGIN = 0.03
OPEN_TOL = 0.005
PLACE_CLEAR = 0.004  # target bottom above the place top at release (= truth)
RETREAT_ABOVE = 0.06  # after release: TCP lower than object top + 6 cm and within 5 cm xy -> move up 10 cm first
RETREAT_XY = 0.05
STUCK_M = 0.005
APPROACH_STEPS = ("above_target", "descend_close", "lift_clear", "reopen")
CARRY_STEPS = ("carry_up", "carry_over", "lower_open")


def stuck(last_line: str, prev_cmd: dict | None, label_cmd: dict | None) -> bool:
    """The last executed move was BLOCKED and the truth would send the same target again: the truth has no good
    answer here (it would teach 'repeat a blocked point', the proxy's failure) -> the sample is dropped."""
    if "BLOCKED" not in (last_line or "") or not prev_cmd or not label_cmd:
        return False
    a, b = prev_cmd.get("position_m"), label_cmd.get("position_m")
    return a is not None and b is not None and float(np.linalg.norm(np.subtract(a, b))) < STUCK_M


def _r(p) -> list:
    return [round(float(v), 3) for v in p]


def place_top(place: str, table_z: float) -> float:
    return table_z + (obj_height(place) if place != "o11" else 0.0)


def plan(st: dict, info: dict, table_z: float, w_open: float):
    """-> (step, command dict | None). None only for step 'tipped' (no label)."""
    tg, pl = info["tgt"], info["place"]
    pred = st["pred"]
    tcp = np.asarray(st["tcp"], float)
    c, p = np.asarray(st["obj"][tg], float), np.asarray(st["obj"][pl], float)
    h = obj_height(tg)
    hold = pred.get(f"holding({tg})") is True
    if pred.get(f"on({tg},{pl})") is True and not hold:
        top = c[2] + h / 2
        if tcp[2] < top + RETREAT_ABOVE and np.linalg.norm(tcp[:2] - c[:2]) < RETREAT_XY:
            return "retreat", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], tcp[2] + ABOVE_DZ]),
                               "gripper": "keep"}
        return "done", {"mode": "stop"}
    if not hold and pred.get(f"upright({tg})") is False:
        return "tipped", None
    if hold:
        put = np.array([p[0], p[1], place_top(pl, table_z) + (tcp[2] - (c[2] - h / 2)) + PLACE_CLEAR])
        if np.linalg.norm(tcp[:2] - p[:2]) < NEAR_XY:
            return "lower_open", {"mode": "eef", "position_m": _r(put), "gripper": "open"}
        if tcp[2] >= table_z + CARRY_DZ - NEAR_XY:
            return "carry_over", {"mode": "eef", "position_m": _r([p[0], p[1], table_z + CARRY_DZ]), "gripper": "keep"}
        return "carry_up", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], table_z + CARRY_DZ]), "gripper": "keep"}
    if float(st["grip_w"]) < w_open - OPEN_TOL:
        return "reopen", {"mode": "gripper", "gripper": "open"}
    g = np.array([c[0], c[1], table_z + h - GRASP_BELOW_TOP_M])
    above = g + [0.0, 0.0, ABOVE_DZ]
    dxy = float(np.linalg.norm(tcp[:2] - g[:2]))
    if dxy < NEAR_XY and tcp[2] <= above[2] + NEAR_XY:
        return "descend_close", {"mode": "eef", "position_m": _r(g), "gripper": "close"}
    if tcp[2] < table_z + h + LOW_MARGIN:
        return "lift_clear", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], above[2]]), "gripper": "keep"}
    return "above_target", {"mode": "eef", "position_m": _r(above), "gripper": "keep"}


def phase_of(step: str) -> str:
    return "approach" if step in APPROACH_STEPS else ("carry" if step in CARRY_STEPS else step)


def _texts(step: str, tn: str, pn: str):
    grasp, carry, put = f"lower to the {tn} and close on it", f"carry it above the {pn}", "put it down and release it"
    table = {
        "above_target": (f"move the TCP about 10 cm above the {tn}", [grasp, carry, put], []),
        "descend_close": (grasp, [carry, put], []),
        "lift_clear": ("lift the gripper clear before moving sideways", [f"move above the {tn}", grasp, carry, put],
                       []),
        "reopen": ("reopen the gripper: the close caught nothing", [f"move above the {tn}", grasp, carry, put], []),
        "carry_up": (f"lift the {tn} to carrying height", [carry, put], [f"grasp the {tn}"]),
        "carry_over": (f"carry the {tn} above the {pn}", [put], [f"grasp the {tn}"]),
        "lower_open": (f"lower the {tn} onto the {pn} and release it", [], [f"grasp the {tn}"]),
        "retreat": ("move the gripper up away from the released object", [],
                    [f"grasp the {tn}", f"place the {tn} on the {pn}"]),
        "done": ("task complete", [], [f"grasp the {tn}", f"place the {tn} on the {pn}"]),
    }
    return table[step]


def status_of(step: str, first: bool, last_line: str, prev_failed: bool) -> str:
    if first:
        return "not_started"
    failed = step == "reopen" or "BLOCKED" in (last_line or "")
    if failed:
        return "failed"
    return "recovered" if prev_failed else "progressing"


def evidence_of(step: str, st: dict, tn: str, last_line: str) -> str:
    t = np.asarray(st["tcp"], float)
    s = f"TCP at ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}) m, pad gap {float(st['grip_w']) * 100:.1f} cm"
    if step == "reopen":
        s += "; the gripper closed with nothing between the pads"
    elif step in CARRY_STEPS:
        s += f"; the pads stopped on the {tn}"
    if "BLOCKED" in (last_line or ""):
        s += "; the last move was blocked"
    elif "clipped" in (last_line or ""):
        s += "; the last target was clipped"
    return s


def label(st: dict, info: dict, table_z: float, w_open: float, first: bool, last_line: str = "",
          prev_failed: bool = False):
    """-> {"step", "phase", "command", "status", "answer" (JSON text)} or None when the state has no label."""
    step, cmd = plan(st, info, table_z, w_open)
    if cmd is None:
        return None
    tn, pn = OBJ_NAME.get(info["tgt"], info["tgt"]), OBJ_NAME.get(info["place"], info["place"])
    doing, remaining, done = _texts(step, tn, pn)
    status = status_of(step, first, last_line, prev_failed)
    ans = {"assessment": {"task_progress": {"verified_completed": done, "currently_attempting": doing,
                                            "remaining": remaining},
                          "execution_status": status, "evidence": evidence_of(step, st, tn, last_line),
                          "evidence_view": "both", "confidence": "high"},
           "command": cmd, "reason": f"Next: {doing}."}
    return {"step": step, "phase": phase_of(step), "command": cmd, "status": status, "answer": json.dumps(ans)}
