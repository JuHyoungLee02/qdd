"""Decision-question answers v2: determined by the observable state (docs/stage3/results/labels_v2.md, canon §53).

The old oracle was the planner's COMMANDED TCP motion over the next 0.33 s (command lag, close/open timers). Here
the answer is the remaining displacement Δ = G - g from the ACTUAL gripper fingertip midpoint g to the goal point G
of the current motion sub-phase, both from the snapshot's stored observation (obs.raw, table frame: x/y = robot base
x/y, z = height above the table top). The sub-phase is chosen from observables only (contract stage, gripper state,
geometry), with the planner's goal geometry (sim/planner.py _goal) applied to actual object poses.

code_rule_v2 applies the same functions to the numbers an S1 text (e3lite.state_text) carries -- the gate.
"""
from __future__ import annotations

import math
import re

import numpy as np

from .e3lite import parse_geometry
from .sim.planner import MAG_BINS
from .sim.snapshot import stage_of

DEADBAND_M = 0.01
ALIGN_XY_M = 0.015  # planner REACH_TOL_FAST_M
APPROACH_ABOVE_TOP_M, GRASP_BELOW_TOP_M = 0.10, 0.018  # planner constants
CARRY_Z_M, PLACE_CLEAR_M, RETREAT_UP_M = 0.20, 0.003, 0.10
MUG_HALF_H, TRAY_HALF_H = 0.0475, 0.0075  # scene OBJ_GEOM (the text does not carry sizes)
MAG_EDGES_M = [math.sqrt(a[1] * b[1]) for a, b in zip(MAG_BINS, MAG_BINS[1:])]
EXIT = {"S1": ("holding(o3)", "lifted(o3)"), "S2": ("on(o3,o5)",)}
QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase_choice", "progress")
_XY = {(1, 0): "plus_x", (1, 1): "plus_x_plus_y", (0, 1): "plus_y", (-1, 1): "minus_x_plus_y", (-1, 0): "minus_x",
       (-1, -1): "minus_x_minus_y", (0, -1): "minus_y", (1, -1): "plus_x_minus_y", (0, 0): "none_xy"}


# ------------------------------------------------------------------------------------------ answers from Δ
def _sgn(v: float) -> int:
    return 0 if abs(v) < DEADBAND_M else (1 if v > 0 else -1)


def dir_xy_label(d) -> str:
    return _XY[(_sgn(d[0]), _sgn(d[1]))]


def dir_z_label(d) -> str:
    return {0: "none_z", 1: "up", -1: "down"}[_sgn(d[2])]


def mag_label(d) -> str:
    n = float(np.linalg.norm(np.asarray(d, float)))
    for (name, _), edge in zip(MAG_BINS, MAG_EDGES_M):
        if n < edge:
            return name
    return MAG_BINS[-1][0]


def target_label(stage: str, tgt: str = "o3", place: str = "o5") -> str:
    return tgt if stage == "S1" else place


def _exit(stage: str, tgt: str = "o3", place: str = "o5") -> tuple:
    if (tgt, place) == ("o3", "o5"):
        return EXIT[stage]
    return (f"holding({tgt})", f"lifted({tgt})") if stage == "S1" else (f"on({tgt},{place})",)


def phase_label(stage: str, gstate: str, facts: dict, d, tgt: str = "o3", place: str = "o5") -> str:
    """hold: closed_empty, or S2 with holding(o3) and on(o3,o5) both not true. next: every exit predicate of the
    stage true, or the sub-goal reached (none_xy and none_z). Otherwise continue. (R2: o3 / o5 = the task's
    target / place.)"""
    if gstate == "closed_empty" or (stage == "S2" and facts.get(f"holding({tgt})") is not True
                                     and facts.get(f"on({tgt},{place})") is not True):
        return "hold"
    if all(facts.get(p) is True for p in _exit(stage, tgt, place)):
        return "next"
    if dir_xy_label(d) == "none_xy" and dir_z_label(d) == "none_z":
        return "next"
    return "continue"


# ------------------------------------------------------------------------------------------ sub-phase and goal
def gripper_state(pred: dict, tgt: str = "o3") -> str:
    if pred.get("gripper_open"):
        return "open"
    return "closed_holding" if pred.get(f"holding({tgt})") else "closed_empty"


def _motion(stage: str, gstate: str, rel: dict, tgt: str = "o3", place: str = "o5") -> str:
    """rel: {obj: centre - gripper [m]}."""
    if gstate == "closed_empty":
        return "wait"
    if stage == "S1":
        if gstate == "open":
            return "approach" if math.hypot(rel[tgt][0], rel[tgt][1]) > ALIGN_XY_M else "grasp"
        return "lift"
    if gstate == "open":
        return "retreat"
    return "carry" if math.hypot(rel[place][0], rel[place][1]) > ALIGN_XY_M else "place"


def _delta(M: str, grip_z: float, rel: dict, hm: float = MUG_HALF_H, hr: float = TRAY_HALF_H, tgt: str = "o3",
           place: str = "o5") -> np.ndarray:
    """Δ = G - g for sub-phase M (goal geometry of planner._goal on actual poses). hm / hr: half heights of the
    target / place object."""
    if M == "wait":
        return np.zeros(3)
    if M in ("lift", "retreat"):
        z = CARRY_Z_M - grip_z if M == "lift" else rel[tgt][2] + hm - GRASP_BELOW_TOP_M + RETREAT_UP_M
        return np.array([0.0, 0.0, z])
    if M in ("approach", "grasp"):
        m = rel[tgt]
        up = hm + APPROACH_ABOVE_TOP_M if M == "approach" else hm - GRASP_BELOW_TOP_M
        return np.array([m[0], m[1], m[2] + up])
    r = rel[place]
    if M == "carry":
        return np.array([r[0], r[1], CARRY_Z_M - grip_z])
    if M == "place":
        gap = (rel[tgt][2] - hm) - (r[2] + hr)  # target bottom above the place object's top
        return np.array([r[0], r[1], -gap + PLACE_CLEAR_M])
    raise ValueError(M)


def task_objs(line) -> tuple:
    """(target, place) of the line's task (R2 field `task`; pool lines without it = mug o3 -> tray o5)."""
    from .sim.tasks import TASKS, check_task
    t = TASKS[check_task(line.get("task", "mug_tray"))]
    return t.target, t.place


def _obs(state, tgt: str = "o3", place: str = "o5"):
    raw = state["obs"]["raw"]
    g = np.asarray(raw["grip"]["pos"], float)
    rel = {k: np.asarray(raw["objs"][k]["pos"], float) - g for k in state["present"] if k in raw["objs"]}
    he = {k: raw["objs"][k].get("he") for k in (tgt, place) if k in raw["objs"]}
    hm = he[tgt][2] if he.get(tgt) else MUG_HALF_H
    hr = he[place][2] if he.get(place) else TRAY_HALF_H
    return g, rel, hm, hr


def goal_point(phase: str, state, tgt: str = "o3", place: str = "o5") -> np.ndarray:
    """G for sub-phase `phase` (approach/grasp/lift/carry/place/retreat/wait) from the snapshot state's poses."""
    g, rel, hm, hr = _obs(state, tgt, place)
    return g + _delta(phase, float(g[2]), rel, hm, hr, tgt, place)


def motion_phase(line) -> str:
    tgt, place = task_objs(line)
    g, rel, _, _ = _obs(line["state"], tgt, place)
    return _motion(stage_of(line["phase"]), gripper_state(line["pred"], tgt), rel, tgt, place)


def delta(line):
    """(sub-phase, Δ = G - g [m]) of one snapshot line."""
    tgt, place = task_objs(line)
    M = motion_phase(line)
    g, rel, hm, hr = _obs(line["state"], tgt, place)
    return M, _delta(M, float(g[2]), rel, hm, hr, tgt, place)


def _answers(stage, gstate, facts, M, d, tgt: str = "o3", place: str = "o5") -> dict:
    return {"dir_xy": dir_xy_label(d), "dir_z": dir_z_label(d), "mag_coarse": mag_label(d),
            "target": target_label(stage, tgt, place),
            "phase_choice": phase_label(stage, gstate, facts, d, tgt, place), "motion_phase": M}


def labels(line) -> dict:
    """v2 answers (oracle-field names) + sub-phase and Δ for one snapshot line; progress = the old oracle value."""
    tgt, place = task_objs(line)
    stage, gstate = stage_of(line["phase"]), gripper_state(line["pred"], tgt)
    M, d = delta(line)
    out = _answers(stage, gstate, line["pred"], M, d, tgt, place)
    out["progress"] = (line.get("oracle") or {}).get("progress")
    out["delta_m"] = [round(float(v), 5) for v in d]
    out["goal_m"] = [round(float(v), 5) for v in goal_point(M, line["state"], tgt, place)]
    return out


# ------------------------------------------------------------------------------------------ S1-text code rule
_YN = {"yes": True, "no": False}


def parse_facts(text: str) -> dict:
    m = re.search(r"^facts: (.*)$", text, re.M)
    return {k: _YN.get(v) for k, v in re.findall(r"(\S+)=(\S+)", m.group(1) if m else "")}


def code_rule_v2(text: str) -> dict:
    """The v2 answers from an S1 text only: stage, gripper, facts and the printed geometry numbers (cm)."""
    p = parse_geometry(text)
    stage = p["stage"]
    gs = p["gripper_state"]
    gstate = "open" if gs == "open" else ("closed_holding" if gs.startswith("closed_holding") else "closed_empty")
    grip_z = p["gripper"][2] / 100
    rel = {k: np.asarray(v, float) / 100 for k, v in p.items() if re.fullmatch(r"o\d+", k)}
    M = _motion(stage, gstate, rel)
    d = _delta(M, grip_z, rel)
    out = _answers(stage, gstate, parse_facts(text), M, d)
    out["progress"] = "valid_progress"
    return out
