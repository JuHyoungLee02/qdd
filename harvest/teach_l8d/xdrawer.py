"""L8-X drawer opening dr__<piece>__<handle> (prereg_l8x_tasks 2.4 + change 6; pure).

The drawer handle is taken from ABOVE (top drawers whose handle has open space above it and >= 12 mm to the drawer
front, tools/l8x_assets/handle_topdown.py), so the command vocabulary is the existing eef + gripper one (no new
prompt version). Truth plan: above_handle -> descend_close (pads around the handle bar, closing along world x) ->
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
HELD_W = 0.035  # pad gap below this = closed on the handle bar (bars are 1-3 cm thick)
JUDGE_SHARE = 0.8
STEPS = ("above_handle", "descend_close", "pull", "release", "retreat")
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
        if w < w_open - OPEN_TOL:
            return "release", {"mode": "gripper", "gripper": "open"}
        if tcp[2] < h[2] + ABOVE_DZ - 0.02:
            return "retreat", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], h[2] + ABOVE_DZ]), "gripper": "keep"}
        return "done", {"mode": "stop"}
    if w < HELD_W and near:
        goal = h + u * min(PULL_STEP, target - q)
        return "pull", {"mode": "eef", "position_m": _r(goal), "gripper": "keep"}
    if w < w_open - OPEN_TOL:  # closed but not on the handle: open again
        return "release", {"mode": "gripper", "gripper": "open"}
    above = h + np.array([0.0, 0.0, ABOVE_DZ])
    if np.linalg.norm(tcp[:2] - h[:2]) <= NEAR_XY and tcp[2] <= above[2] + NEAR_XY:
        return "descend_close", {"mode": "eef", "position_m": _r(h), "gripper": "close"}
    if tcp[2] < h[2] + 0.05 and np.linalg.norm(tcp[:2] - h[:2]) > NEAR_XY:  # low and off the handle: rise first
        return "above_handle", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], above[2]]), "gripper": "keep"}
    return "above_handle", {"mode": "eef", "position_m": _r(above), "gripper": "keep"}


def texts(step: str, pn: str = "drawer"):
    grip, pull, rel = f"lower onto the {pn} handle and close on it", f"pull the {pn} open", "release the handle"
    table = {"above_handle": (f"move the TCP about 10 cm above the {pn} handle", [grip, pull, rel], []),
             "descend_close": (grip, [pull, rel], []),
             "pull": (pull, [rel], [f"grasp the {pn} handle"]),
             "release": (rel, [], [f"pull the {pn} open"]),
             "retreat": ("move the gripper up away from the handle", [], [f"pull the {pn} open", rel])}
    return table[step]


def success_drawer(q_end: float, grip_w_end: float, w_open: float, root_move_m: float,
                   open_target: float = OPEN_TARGET) -> bool:
    return (q_end >= JUDGE_SHARE * open_target and grip_w_end >= w_open - 0.01 and root_move_m <= 0.01)


# --------------------------------------------------------------------------------------------- frozen list
def handle_body(collider_prim: str) -> str:
    """'<...>_handle_PrimitiveCollider_2' -> '<...>_handle' (the handle's rigid body)."""
    return collider_prim.split("_PrimitiveCollider")[0]


def drawer_list(handles_json: dict) -> list:
    """[(piece, handle body, handle top z)] of the top-down graspable handles, one per handle body, sorted."""
    out = {}
    for piece, r in handles_json.items():
        for hd in r.get("handles", []):
            if hd.get("ok"):
                out.setdefault((piece, handle_body(hd["prim"])), hd["top_z"])
    return sorted((p, b, z) for (p, b), z in out.items())


def task_id(piece: str, body: str) -> str:
    return f"dr__{piece}__{body}"


def gate_pick(items: list, seed: int):
    return items[int(hashlib.sha256(f"drawer-gate:{seed}".encode()).hexdigest()[:8], 16) % len(items)]


def load_list(root: str | None = None) -> dict:
    p = os.path.join(root or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."), LIST)
    return json.load(open(p))
