"""L8-X drawer opening dr__<piece>__<handle> (prereg_l8x_tasks 2.4 + changes 6-10; pure).

Since change 10 the truth plan is plan_drawer_front (front grasp, "orient": "front"); plan_drawer below is the
top-down plan of changes 6-9, kept for the record (its grasp is blocked by the gripper housing on every piece).

The drawer handle is taken from ABOVE (top drawers whose handle has open space above it and >= 12 mm to the drawer
front, tools/l8x_assets/handle_topdown.py). Change 7: the open gripper command carries an optional "width_m"
(pre-shape to PRESHAPE_W so the rear finger stays clear of the drawer front) -> new prompt version (+x2) for data;
the approach runs at info["clear_z"] (above the piece top). Truth plan: preshape -> above_handle -> descend (open
pads around the bar) -> close (change 9: a separate gripper command, along world x) ->
pull (towards the robot along the drawer's slide axis, <= 5 mm per command, until the joint reaches the target
opening) -> release (open) -> retreat (up 10 cm) -> done.
State the runner supplies: st["tcp"], st["grip_w"], st["handle"] (handle bar centre, world), st["joint"] (drawer
joint value, m, 0 = closed); info: "pull_dir" (world unit vector of the opening direction), "open_target" (m).
Judge: joint >= 0.8 x open_target held at the end, the gripper released (open), the piece's root fixed."""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np

ABOVE_DZ = 0.10
NEAR_XY = 0.012
NEAR_Z = 0.015
PULL_STEP = 0.005
OPEN_TARGET = 0.20
OPEN_TOL = 0.004
HELD_W = 0.018  # pad gap below this = closed on the handle bar (bars are ~1 cm thick; change 8)
PRESHAPE_W = 0.025  # change 7/8: pads opened only this wide around the bar (rear pad stays < 2 cm behind it)
JUDGE_SHARE = 0.8
STANDOFF_MIN = 0.025  # change 7: gap behind the bar for the pre-shaped rear finger (handle_topdown asks only 12 mm)
STEPS = ("preshape", "above_handle", "descend", "close", "pull", "release", "retreat")
LIST = "docs/stage3/l8x_drawer_list.json"


def _r(v):
    return [round(float(x), 4) for x in v]


def plan_drawer(st: dict, info: dict, w_open: float):
    tcp = np.asarray(st["tcp"], float)
    h = np.asarray(st["handle"], float)
    q = float(st["joint"])
    target = float(info.get("open_target", OPEN_TARGET))
    u = np.asarray(info["pull_dir"], float)
    u = u / max(np.linalg.norm(u), 1e-9)
    w = float(st["grip_w"])
    near = np.linalg.norm(tcp[:2] - h[:2]) <= NEAR_XY and abs(tcp[2] - h[2]) <= NEAR_Z
    if q >= target - OPEN_TOL:
        if w < PRESHAPE_W - 0.006:
            return "release", {"mode": "gripper", "gripper": "open", "width_m": PRESHAPE_W}
        if tcp[2] < h[2] + ABOVE_DZ - 0.02:
            return "retreat", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], h[2] + ABOVE_DZ]), "gripper": "keep"}
        return "done", {"mode": "stop"}
    if w < HELD_W and near:
        goal = h + u * min(PULL_STEP, target - q)
        return "pull", {"mode": "eef", "position_m": _r(goal), "gripper": "keep"}
    if near and w >= PRESHAPE_W - 0.006:  # change 9: close only once the pads are around the bar
        return "close", {"mode": "gripper", "gripper": "close"}
    if w < PRESHAPE_W - 0.006:  # closed but not on the handle: open to the pre-shape again
        return "release", {"mode": "gripper", "gripper": "open", "width_m": PRESHAPE_W}
    if w > PRESHAPE_W + 0.010:  # change 7: narrow the open fingers first (a 107 mm spread hits the drawer front)
        return "preshape", {"mode": "gripper", "gripper": "open", "width_m": PRESHAPE_W}
    clear = max(h[2] + ABOVE_DZ, float(info.get("clear_z", 0.0)))  # above the piece's top (change 7)
    xy_near = np.linalg.norm(tcp[:2] - h[:2]) <= NEAR_XY
    if xy_near and tcp[2] <= clear + NEAR_XY:
        return "descend", {"mode": "eef", "position_m": _r(h), "gripper": "keep"}  # change 9: no close on the way
    if not xy_near and tcp[2] < clear - 0.02:  # off the handle and below the clear height: rise first
        return "above_handle", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], clear]), "gripper": "keep"}
    return "above_handle", {"mode": "eef", "position_m": _r([h[0], h[1], clear]), "gripper": "keep"}


FRONT_BACK = 0.10  # change 10: pre-grasp point this far in front of the bar (towards the robot, along pull_dir)
FRONT_GRASP = 0.012  # pad centre this far in front of the bar centre (fingertips stay out of the drawer front)
FRONT_W = 0.040  # change 11: front pre-shape (fingers vertical; 2.5 cm let the IK z sag of ~1 cm hit the bar)
FRONT_PULL = 0.010  # change 11: 1 cm per pull command, the TCP lead over the grasp point capped at 1 cm
FRONT_LEAD = 0.010
FRONT_RETREAT = 0.035  # change 12: back off 3.5 cm from the released handle (was FRONT_BACK 10 cm)
STEPS_FRONT = ("preshape", "front_of_handle", "insert", "close", "pull", "release", "retreat")
STEPS_FRONT_ALL = STEPS_FRONT + ("reopen", "done")


def plan_drawer_front(st: dict, info: dict, w_open: float):
    """change 10: grasp the bar from the front (gripper axis along -pull_dir, fingers closing vertically); the
    top-down grasp is blocked by the gripper housing (~9 cm along the closing axis) meeting the piece's top edge
    whenever the bar is > ~3 cm below the top (all 15 pieces). Commands carry "orient": "front" (+x2 vocabulary)."""
    tcp = np.asarray(st["tcp"], float)
    h = np.asarray(st["handle"], float)
    q = float(st["joint"])
    target = float(info.get("open_target", OPEN_TARGET))
    u = np.asarray(info["pull_dir"], float)
    u = u / max(np.linalg.norm(u), 1e-9)
    w = float(st["grip_w"])
    g = h + u * FRONT_GRASP
    pre = g + u * FRONT_BACK
    along = float((tcp - g) @ u)  # > 0: the TCP is in front of the grasp point (short of it / leading the pull)
    side = tcp - g - u * along  # offset across the approach line
    near = np.linalg.norm(side) <= NEAR_XY and -0.005 <= along <= NEAR_Z  # change 11: across and along apart

    def eef(step, p):
        return step, {"mode": "eef", "position_m": _r(p), "gripper": "keep", "orient": "front"}

    if q >= target - OPEN_TOL:
        if w < FRONT_W - 0.006:
            return "release", {"mode": "gripper", "gripper": "open", "width_m": FRONT_W}
        if float((tcp - g) @ u) < FRONT_RETREAT - 0.01:  # change 12: short retreat (the x >= 0.25 m box)
            return eef("retreat", tcp + u * (FRONT_RETREAT - float((tcp - g) @ u)))
        return "done", {"mode": "stop"}
    if w < HELD_W and near:
        # from the TCP (it can stop short of g) along the pull line, the lead capped so the TCP never runs away
        return eef("pull", g + u * (min(max(along, 0.0), FRONT_LEAD) + min(FRONT_PULL, target - q)))
    if near and w >= FRONT_W - 0.006:
        return "close", {"mode": "gripper", "gripper": "close"}
    if w < FRONT_W - 0.006:
        return "reopen", {"mode": "gripper", "gripper": "open", "width_m": FRONT_W}  # change 12: the close missed
    if w > FRONT_W + 0.010:
        return "preshape", {"mode": "gripper", "gripper": "open", "width_m": FRONT_W}
    if np.linalg.norm(side) <= NEAR_XY and float((tcp - g) @ u) <= FRONT_BACK + NEAR_XY:
        return eef("insert", g)
    return eef("front_of_handle", pre)


def texts_front(step: str, pn: str = "drawer"):
    """change 12: assessment texts of the front plan (doing, remaining, done)."""
    fr, ins = f"move the open fingers in front of the {pn} handle", "move the fingers forward around the handle bar"
    close, pull, rel, back = "close the fingers on the handle", f"pull the {pn} open", "release the handle", \
        "move the gripper back from the handle"
    table = {"preshape": ("open the fingers just wider than the handle bar", [fr, ins, close, pull, rel, back], []),
             "front_of_handle": (fr, [ins, close, pull, rel, back], []),
             "insert": (ins, [close, pull, rel, back], [fr]),
             "close": (close, [pull, rel, back], [ins]),
             "reopen": ("reopen the fingers: the close missed the handle", [fr, ins, close, pull, rel, back], []),
             "pull": (pull, [rel, back], ["grasp the handle"]),
             "release": (rel, [back], [pull]),
             "retreat": (back, [], [pull, rel]),
             "done": ("nothing: the task is complete", [], [pull, rel, back])}
    return table[step]


def texts(step: str, pn: str = "drawer"):
    grip, pull, rel = f"lower onto the {pn} handle and close on it", f"pull the {pn} open", "release the handle"
    close = f"close the fingers on the {pn} handle"
    table = {"preshape": ("open the fingers just wider than the handle bar", [f"move above the {pn} handle", grip,
                                                                                 pull, rel], []),
             "above_handle": (f"move the TCP about 10 cm above the {pn} handle", [grip, pull, rel], []),
             "descend": (f"lower the open fingers around the {pn} handle bar", [close, pull, rel], []),
             "close": (close, [pull, rel], [f"lower the fingers around the {pn} handle"]),
             "pull": (pull, [rel], [f"grasp the {pn} handle"]),
             "release": (rel, [], [f"pull the {pn} open"]),
             "retreat": ("move the gripper away from the handle", [], [f"pull the {pn} open", rel]),
             "front_of_handle": (f"move the open fingers in front of the {pn} handle", [close, pull, rel], []),
             "insert": (f"move the fingers forward around the {pn} handle bar", [close, pull, rel], [])}
    return table[step]


def success_drawer(q_end: float, grip_w_end: float, w_open: float, root_move_m: float,
                   open_target: float = OPEN_TARGET) -> bool:
    return (q_end >= JUDGE_SHARE * open_target and grip_w_end >= PRESHAPE_W - 0.006 and root_move_m <= 0.01)


# --------------------------------------------------------------------------------------------- frozen list
def handle_body(collider_prim: str) -> str:
    """'<...>_handle_PrimitiveCollider_2' -> '<...>_handle' (the handle's rigid body)."""
    return collider_prim.split("_PrimitiveCollider")[0]


BAR_MIN = 0.008  # change 11: the pinched bar (the body's longest collider) is >= 8 mm in both cross dimensions
REACH_MIN_Z = 0.50  # change 11: lower handles need the lift below its -0.5 limit (Side_Table_306_2 at 0.44 m)


def drawer_list(handles_json: dict) -> list:
    """[(piece, handle body, handle top z)] of the graspable handles, one per handle body, sorted."""
    out, bars = {}, {}
    for piece, r in handles_json.items():
        for hd in r.get("handles", []):
            key, size = (piece, handle_body(hd["prim"])), hd.get("size", [1.0, 1.0, 1.0])
            if key not in bars or size[1] > bars[key][1]:
                bars[key] = size
            if hd.get("ok") and hd.get("standoff_m", 1.0) >= STANDOFF_MIN and hd.get("front_ok", True) \
                    and hd["top_z"] >= REACH_MIN_Z:  # change 11
                out.setdefault(key, hd["top_z"])
    return sorted((p, b, z) for (p, b), z in out.items() if min(bars[(p, b)][0], bars[(p, b)][2]) >= BAR_MIN)


def task_id(piece: str, body: str) -> str:
    return f"dr__{piece}__{body}"


def gate_pick(items: list, seed: int):
    return items[int(hashlib.sha256(f"drawer-gate:{seed}".encode()).hexdigest()[:8], 16) % len(items)]


def load_list(root: str | None = None) -> dict:
    p = os.path.join(root or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."), LIST)
    return json.load(open(p))
