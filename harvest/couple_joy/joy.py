"""Joystick interface between a point-then-act commander (planner or truth) and the fused VLA (NOW.md §1, §1-1;
canon §96 보충 5-6; docs/stage3/coupling_program.md). Pure numpy.

The commander keeps authority: it sends a goal (xyz from the head point + depth) with a height intent and a gripper
intent. Every decision step (0.33 s) the code turns 'goal - fingertip' into the VLA's joystick decision with the
SAME labeler the VLA was trained on (labels_v2: per-axis 1 cm deadband, magnitude bin of the remaining distance),
names the VLA phase from the commander's intent, and the VLA turns that into a joint chunk. The gripper moves only
in the direction the commander allowed (grip_gate)."""
from __future__ import annotations

import numpy as np

from .. import labels_v2 as L

MAX_DQ = 0.04  # rad per control tick (NOW.md §4, the planner's MAX_DQ_RAD)
S1 = ("approach", "descend", "close", "lift")


def joystick(goal, tip) -> dict:
    d = np.asarray(goal, float) - np.asarray(tip, float)
    return {"dir_xy": L.dir_xy_label(d), "dir_z": L.dir_z_label(d), "mag_coarse": L.mag_label(d)}


def vla_phase(intent: dict, holding: bool, released: bool, arrived: bool) -> str:
    """The VLA skill phase (stage-B phase_id) for the commander's current intent."""
    mode, grip, h = intent.get("mode"), intent.get("gripper"), intent.get("height")
    if mode == "gripper":
        return "close" if grip == "close" else "open"
    if arrived and grip in ("close", "open"):
        return grip
    if holding:
        if mode == "edit" or h == "lift":
            return "lift"
        if h in ("place", "grasp"):
            return "place_descend"
        return "carry"
    if released:
        return "retreat"
    if mode == "edit" or h == "lift":
        return "retreat"
    return "descend" if h in ("grasp", "place") else "approach"


def committed(phase: str, joy: dict, tgt: str, place: str, grip_closed_empty: bool) -> dict:
    """The five decision slots the expert is conditioned on (stage-B vocab: dir_xy, dir_z, mag_coarse, target,
    phase continue / next / hold)."""
    if grip_closed_empty:
        ph = "hold"
    elif joy["dir_xy"] == "none_xy" and joy["dir_z"] == "none_z":
        ph = "next"
    else:
        ph = "continue"
    return dict(joy, target=tgt if phase in S1 else place, phase=ph)


def clamp_step(q_prev, q_target, max_dq: float = MAX_DQ) -> np.ndarray:
    q_prev = np.asarray(q_prev, float)
    return q_prev + np.clip(np.asarray(q_target, float) - q_prev, -max_dq, max_dq)


def grip_gate(w_prev: float, w_vla: float, allow, w_open: float, w_close: float) -> float:
    """allow None: hold; 'close': follow the VLA only downward, not below w_close; 'open': only upward, <= w_open."""
    if allow == "close":
        return float(min(w_prev, max(w_vla, w_close)))
    if allow == "open":
        return float(max(w_prev, min(w_vla, w_open)))
    return float(w_prev)
