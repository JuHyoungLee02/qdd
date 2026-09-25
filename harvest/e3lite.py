"""E3-lite state representations S0/S1/S2 and the S1-only code-rule upper bound (docs/stage3/results/e3lite.md).

S0 = the snapshot's ser-A-min text (serialize_state; ser-A-min-2 only adds the DecCall's (b) `last_step:` line after
the chosen state, canon §77). S1 = S0 + a geometry block (robot base frame line; gripper position; per
present object the centre offset from the gripper in cm, rounded to 1 cm, plus distance). S2 = S1 + the offsets as
mag_coarse bin names. Built offline from the snapshot's stored observation (state.obs.raw, table frame = robot base
x/y, z = height above the table top), no Isaac.

code_rule: the oracle planner's goal logic (sim/planner.py _goal / next_phase) applied to the numbers an S1 text
carries; answers use the same binning function as the oracle (planner.oracle_answer).
"""
from __future__ import annotations

import math
import re

import numpy as np

from .deccall_snap import rotate  # noqa: F401  (re-exported for the E3-lite tools)
from .sim.planner import DIR_EPS_M, MAG_BINS, oracle_answer
from .sim.snapshot import SPEC_NAMES

FRAME_LINE = ("geometry (robot base frame: +x forward away from the robot, +y robot left, +z up; cm; "
              "offsets = object centre minus gripper):")
T_C = 0.33
# planner constants (sim/planner.py, sim/scene.py OBJ_GEOM), metres
MUG_HALF_H, TRAY_HALF_H = 0.0475, 0.0075
APPROACH_ABOVE_CENTRE = MUG_HALF_H + 0.10  # goal = mug top + 10 cm
DESCEND_ABOVE_CENTRE = MUG_HALF_H - 0.018  # pad centre 1.8 cm below the mug top
CARRY_Z, PLACE_CLEAR = 0.20, 0.003
V = {"approach": 0.20, "descend": 0.06, "lift": 0.08, "carry": 0.20, "place_descend": 0.06, "retreat": 0.20}
ALIGN_XY, REACH_TOL = 0.015, 0.006  # REACH_TOL_FAST_M / REACH_TOL_M


def mag_bin(n: float) -> str:
    """The oracle's mag_coarse naming (log-nearest of MAG_BINS; below DIR_EPS_M -> tiny)."""
    if n < DIR_EPS_M:
        return "tiny"
    return MAG_BINS[int(np.argmin([abs(math.log(n) - math.log(v)) for _, v in MAG_BINS]))][0]


def _cm(x: float) -> int:
    return int(round(x * 100))


def _fmt(x: float, step_cm: float, sign: bool = False) -> str:
    """x [m] on a step_cm grid; step 1 prints integers (the E3-lite S1 format), finer steps one decimal (0.5 cm,
    1 mm) or two (below 1 mm)."""
    if step_cm == 1:
        return f"{_cm(x):+d}" if sign else f"{_cm(x)}"
    v = round(x * 100 / step_cm) * step_cm
    nd = 1 if step_cm >= 0.1 else 2
    return f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"


def _geom(state):
    raw = state["obs"]["raw"]
    g = np.asarray(raw["grip"]["pos"], float)
    ids = sorted(state["present"], key=lambda x: int(x[1:]))
    return g, {k: np.asarray(raw["objs"][k]["pos"], float) - g for k in ids}


def geometry_block(state, bins: bool = False, names=SPEC_NAMES, step_cm: float = 1) -> str:
    """step_cm: print grid (1 = the E3-lite S1 format; labels_v2.md allows a finer grid if its gate fails)."""
    g, rel = _geom(state)

    def f(x, sign=False):
        return _fmt(x, step_cm, sign)

    lines = [FRAME_LINE, f"  gripper: x={f(g[0])} y={f(g[1])} z={f(g[2])} (z = height above the table top)"]
    for k, d in rel.items():
        s = f"  {k} {names.get(k, k)}: dx={f(d[0], True)} dy={f(d[1], True)} dz={f(d[2], True)} " \
            f"dist={f(float(np.linalg.norm(d)))}"
        if bins:
            sg = lambda v: "-" if v < 0 else "+"
            s += (f" bins: dx={sg(d[0])}{mag_bin(abs(d[0]))} dy={sg(d[1])}{mag_bin(abs(d[1]))} "
                  f"dz={sg(d[2])}{mag_bin(abs(d[2]))} dist={mag_bin(float(np.linalg.norm(d)))}")
        lines.append(s)
    return "\n".join(lines)


def state_text(line, S: str, step_cm: float = 1) -> str:
    if S == "S0":
        return line["text_state"]
    if S not in ("S1", "S2"):
        raise ValueError(S)
    return line["text_state"] + "\n" + geometry_block(line["state"], bins=S == "S2", step_cm=step_cm)


# ------------------------------------------------------------------------------------------ code rule (UB)
_NUM = r"([+-]?\d+(?:\.\d+)?)"
_OBJ = re.compile(rf"^  (o\d+) [^:]*: dx={_NUM} dy={_NUM} dz={_NUM} dist={_NUM}")
_GRIP = re.compile(rf"^  gripper: x={_NUM} y={_NUM} z={_NUM}")


def _num(v: str):
    return float(v) if "." in v else int(v)


def parse_geometry(text: str) -> dict:
    """Numbers (cm, as printed) and the S0 fields the rule reads: stage id and gripper state."""
    out = {"stage": re.search(r"stage: (S\d)", text).group(1),
           "gripper_state": re.search(r"gripper=(\S+)", text).group(1)}
    for ln in text.split("\n"):
        m = _GRIP.match(ln)
        if m:
            out["gripper"] = tuple(_num(v) for v in m.groups())
        m = _OBJ.match(ln)
        if m:
            out[m.group(1)] = tuple(_num(v) for v in m.groups()[1:4])
    return out


def _goal_rel(stage, gstate, grip_z, rel):
    """(phase, goal - gripper [m]) from the planner's goal logic; rel: {obj: centre - gripper [m]}."""
    o3 = rel.get("o3")
    if gstate == "open" and stage == "S1":
        above = -o3[2]  # gripper height above the mug centre
        if math.hypot(o3[0], o3[1]) > ALIGN_XY or above > APPROACH_ABOVE_CENTRE + ALIGN_XY:
            return "approach", np.array([o3[0], o3[1], o3[2] + APPROACH_ABOVE_CENTRE])
        d = np.array([o3[0], o3[1], o3[2] + DESCEND_ABOVE_CENTRE])
        return ("close", np.zeros(3)) if np.linalg.norm(d) < REACH_TOL else ("descend", d)
    if gstate.startswith("closed_holding"):
        if stage == "S1" and grip_z < CARRY_Z - ALIGN_XY:
            return "lift", np.array([0.0, 0.0, CARRY_Z - grip_z])
        o5 = rel["o5"]
        if math.hypot(o5[0], o5[1]) > ALIGN_XY:
            return "carry", np.array([o5[0], o5[1], CARRY_Z - grip_z])
        gap = (o3[2] - MUG_HALF_H) - (o5[2] + TRAY_HALF_H)  # mug bottom above the tray top
        return "place_descend", np.array([0.0, 0.0, -gap + PLACE_CLEAR])
    if gstate == "open" and stage == "S2":
        if -o3[2] > 0.12:
            return "done", np.zeros(3)
        return "retreat", np.array([0.0, 0.0, 0.10])
    return "none", np.zeros(3)


def code_rule(text: str, raw=None) -> dict:
    """Oracle-key answers for the six questions from an S1 text (raw: the snapshot state -> unrounded numbers)."""
    p = parse_geometry(text)
    if raw is None:
        grip_z = p["gripper"][2] / 100
        rel = {k: np.asarray(v, float) / 100 for k, v in p.items() if re.fullmatch(r"o\d+", k)}
    else:
        g, rel = _geom(raw)
        grip_z = float(g[2])
    stage, gstate = p["stage"], p["gripper_state"]
    phase, d = _goal_rel(stage, gstate, grip_z, rel)
    n = float(np.linalg.norm(d))
    step = V.get(phase, 0.0) * T_C
    disp = d if n <= step else d * (step / n)
    a = oracle_answer(np.zeros(3), disp, 0.0, 0.0)
    target = "o5" if (gstate.startswith("closed_holding") or stage == "S2") else "o3"
    nxt = phase in V and n <= step
    return {"dir_xy": a["dir_xy"], "dir_z": a["dir_z"], "mag_coarse": a["mag_coarse"], "target": target,
            "phase_choice": "next" if nxt else "continue", "progress": "valid_progress"}
