"""Skill geometry for the articulated truth plans (pure numpy): natural, varied handle grasps (no single canonical
pose), contact poses for pushes / presses, follower targets along the joint, v3 label fields, judges.

Tool frame = harvest.l9.grasp9 G: z_G = -a (a = approach, the way the hand moves in), y_G = closing axis, TCP between
the pads. A grasp / contact pose is (R = frame_of(a, c), p = TCP)."""
from __future__ import annotations

import math

import numpy as np

from . import fixtures as FX

STANDOFF = (0.08, 0.12)  # pre-pose distance back along the approach
PITCH_MAX = math.radians(30)  # front grasps tilted down by up to 30 deg (oblique) [가설: natural spread]
YAW_MAX = math.radians(15)
ROLL_MAX = math.radians(10)
PUSH_IN = 0.004  # push follower: target 4 mm past the contact
PRESS_EXTRA = 0.004
FOLLOW_STEP = {"prismatic": 0.03, "door": math.radians(7.0), "knob": math.radians(6.0)}  # line() rejects > 0.15 rad between waypoints (a 12 deg roll failed as "ik")


def frame_of(a, c) -> np.ndarray:
    a = np.asarray(a, float) / np.linalg.norm(a)
    c = np.asarray(c, float) - a * float(np.dot(a, c))
    c = c / np.linalg.norm(c)
    z = -a
    return np.stack([np.cross(c, z), c, z], 1)


def T_pose(R, p) -> np.ndarray:
    return FX.T_of(R, p)


def pad_offset(gr: dict) -> float:
    """Pad-centre distance beyond the TCP along the approach, from the L9v2-ROBOT gripper json (pad_z_range_in_tcp;
    z_G = -a): AI Worker 1.7 cm, Franka 0.1 cm, R1 Pro 0 (smoke 10-02: bars at the TCP sat outside the AI Worker pads)."""
    import json as _j
    import os as _o
    from ..l9 import grasp9 as G9
    name = gr.get("json")
    if not name:
        return 0.0
    p = _o.path.join(G9.DIR, name)
    if not _o.path.exists(p):
        return 0.0
    z = _j.load(open(p, encoding="utf-8")).get("pad_z_range_in_tcp")
    return float(-(z[0] + z[1]) / 2) if z else 0.0


def tip_offset(gr: dict) -> float:
    """Distance from the TCP to the fingertips along the approach (gripper model of harvest.l9.grasp9)."""
    t = gr.get("tip")
    return float(-t) if t is not None else float(gr.get("pad_len", 0.04)) / 2


def _tilt(a, axis, ang):
    return FX.rot_axis(axis, ang) @ np.asarray(a, float)


def grasp_draw(rng) -> dict:
    """Per-episode grasp style draw (natural spread): along-bar offset share, pitch, yaw, roll, standoff."""
    fam = rng.choice(["front", "oblique"], p=[0.6, 0.4])
    return {"u": float(rng.uniform(-1, 1)), "pitch": float(rng.uniform(0, math.radians(10)) if fam == "front"
                                                             else rng.uniform(math.radians(15), PITCH_MAX)),
            "yaw": float(rng.uniform(-YAW_MAX, YAW_MAX)), "roll": float(rng.uniform(-ROLL_MAX, ROLL_MAX)),
            "standoff": float(rng.uniform(*STANDOFF)), "knob_roll": float(rng.uniform(0, math.pi)),
            "flip": bool(rng.random() < 0.5)}


def handle_grasp(hf: dict, gr: dict, draw: dict) -> dict:
    """Grasp pose on a handle frame (handle_frame()): approach into the handle (-fn) tilted down by pitch and turned by
    yaw, closing axis across the bar (rolled by roll), TCP on the bar at the drawn along-bar offset.
    -> {T, T_pre, a, c, p, open_w}."""
    fn = np.asarray(hf["fn"], float)
    a = -fn
    up = np.array([0.0, 0.0, 1.0])
    if hf["type"] == "knob":  # knobs: approach along the knob axis so the turn is a wrist roll (smoke 10-02: a tilted
        pass  # approach made the 60-120 deg turns leave the arm's reach, 'ik' in 9 of 12 follower stops)
    elif abs(a @ up) < 0.9:  # front-facing part: pitch down (approach from above-front), yaw about the vertical
        side_ax = np.cross(a, up)
        side_ax /= np.linalg.norm(side_ax)
        a = _tilt(a, side_ax, -draw["pitch"])
        a = _tilt(a, up, draw["yaw"])
    else:  # top-facing part: tilt the vertical approach a little towards the robot
        a = _tilt(a, np.array([0.0, 1.0, 0.0]), 0.5 * draw["pitch"])
    p = np.asarray(hf["gc"], float).copy()
    typ = hf["type"]
    bar = np.asarray(hf.get("bar", [0, 1.0, 0]), float)
    if typ in ("bar_h", "bar_v"):
        L = float(hf.get("length", 0.1))
        room = max(0.0, L / 2 - float(hf.get("thick", 0.012)) - gr.get("finger_w", 0.02) / 2 - 0.008)
        p = p + bar * draw["u"] * room
        c = np.cross(bar, a)
        if np.linalg.norm(c) < 1e-6:
            c = np.cross(up, a)
    elif typ == "knob":  # pinch the knob BODY across its diameter, closing across the fin (pilot 10-02: pinching the
        c = np.cross(bar, a)  # 1.2 cm fin closed at 2.3-2.9 cm and the turn stalled at 7-42 deg in 8 of 12 episodes)
        if hf.get("body_gc") is not None:
            tip_beyond_pad = tip_offset(gr) - pad_offset(gr)
            off = max(0.0, tip_beyond_pad + 0.003 - float(hf.get("body_h", 0.02)) / 2)  # fingertips clear the panel
            p = np.asarray(hf["body_gc"], float) + fn * off
    elif typ == "knob_pull":  # round cap: any closing direction
        ref = np.cross(up, a) if abs(a @ up) < 0.9 else np.array([0.0, 1.0, 0.0])
        c = _tilt(ref, a, draw["knob_roll"])
    else:
        c = np.cross(up, a) if abs(a @ up) < 0.9 else np.array([0.0, 1.0, 0.0])
    c = _tilt(c / np.linalg.norm(c), a, draw["roll"])
    if draw.get("flip"):
        c = -c
    R = frame_of(a, c)
    th = float(hf.get("thick", 0.012))
    open_w = float(min(gr["max_open"], th + 0.03 + 0.01 * abs(draw["u"])))
    if typ == "knob" and hf.get("dia"):
        open_w = float(min(gr["max_open"], float(hf["dia"]) + 0.025))
    pt = p - a * pad_offset(gr)  # TCP so that the PAD CENTRE sits on the handle (AI Worker pads are 0.7-2.7 cm beyond its TCP)
    T = T_pose(R, pt)
    T_pre = T_pose(R, pt + draw["standoff"] * R[:, 2])  # back along -a (= +z_G)
    return {"T": T, "T_pre": T_pre, "a": a, "c": R[:, 1], "p": p, "open_w": open_w, "pad_off": pad_offset(gr)}


def contact_push(point, normal_in, gr: dict, draw: dict, c_hint=None) -> dict:
    """Closed-finger contact pose: fingertips on `point`, hand moving along normal_in (into the surface).
    -> {T (fingertips touching), T_pre (standoff back), a, c, p}."""
    a = np.asarray(normal_in, float) / np.linalg.norm(normal_in)
    up = np.array([0.0, 0.0, 1.0])
    c = np.asarray(c_hint, float) if c_hint is not None else (np.cross(up, a) if abs(a @ up) < 0.9 else np.array([0, 1.0, 0]))
    c = _tilt(c / np.linalg.norm(c), a, draw["roll"])
    R = frame_of(a, c)
    p = np.asarray(point, float) - a * tip_offset(gr)
    T = T_pose(R, p)
    T_pre = T_pose(R, p - a * draw["standoff"])
    return {"T": T, "T_pre": T_pre, "a": a, "c": R[:, 1], "p": p}


def press_pose(hf: dict, travel: float, gr: dict, draw: dict) -> dict:
    fn = np.asarray(hf["fn"], float)
    r = contact_push(hf["gc"], -fn, gr, draw)
    T_in = r["T"].copy()
    T_in[:3, 3] = r["p"] - fn * (travel + PRESS_EXTRA)
    r["T_in"] = T_in
    return r


def follow_target(T_link_now, T_link_tcp, push_in: float = 0.0, a=None) -> np.ndarray:
    """Hand pose that keeps the grasp / contact relation to the link (+ push_in along the approach)."""
    T = np.asarray(T_link_now, float) @ np.asarray(T_link_tcp, float)
    if push_in and a is not None:
        T = T.copy()
        T[:3, 3] = T[:3, 3] + push_in * np.asarray(a, float)
    return T


def next_value(q_now: float, goal: float, step: float) -> float:
    d = goal - q_now
    return goal if abs(d) <= step else q_now + math.copysign(step, d)


def follow_step(kind: str) -> float:
    return FOLLOW_STEP["prismatic"] if kind in ("drawer", "slide") else FOLLOW_STEP.get(kind, FOLLOW_STEP["door"])


# ------------------------------------------------------------------------------------------------ push objects
def push_plan(obj_c, half, tz: float, direction, dist: float, gr: dict, draw: dict) -> dict:
    """Vertical-hand push (fingers down, closed, their side as a paddle) of an object of box half extents `half`
    (world-aligned approximation) by dist along direction. -> {T_pre_high, T_pre, T_goal, a, c, goal_xy}."""
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    ext = float(abs(d[0]) * half[0] + abs(d[1]) * half[1])
    a = np.array([0.0, 0.0, -1.0])
    # straight-down hand (smoke: a tilted paddle tipped a box pushed away from the robot)
    c = np.array([-d[1], d[0], 0.0])  # closing axis across the push direction: the two fingers side by side
    R = frame_of(a, c)
    fw = float(gr.get("finger_t", 0.012))
    z = tz + 0.015 + tip_offset(gr)  # fingertips 1.5 cm over the table
    start = np.asarray(obj_c, float)[:2] - d[:2] * (ext + fw + 0.012)
    goal_xy = np.asarray(obj_c, float)[:2] + d[:2] * dist
    end = goal_xy - d[:2] * (ext + fw + 0.004)
    p_pre = np.array([start[0], start[1], z])
    return {"T_pre_high": T_pose(R, p_pre + np.array([0, 0, draw["standoff"]])), "T_pre": T_pose(R, p_pre),
            "T_goal": T_pose(R, np.array([end[0], end[1], z])), "a": a, "c": c, "goal_xy": goal_xy, "dir": d}


# ------------------------------------------------------------------------------------------------ labels
def to_px(cam, X) -> list | None:
    """0-1000 image coordinates of world point X in a pinhole camera (harvest Cam: W, H, fx, fy, cx, cy, R, t with
    R = camera->world rotation columns optical x, y, z) or None when behind / outside."""
    R, t = np.asarray(cam.R, float), np.asarray(cam.t, float)
    Xc = (np.asarray(X, float) - t) @ R
    if Xc[2] <= 1e-6:
        return None
    u = cam.fx * Xc[0] / Xc[2] + cam.cx
    v = cam.fy * Xc[1] / Xc[2] + cam.cy
    if not (0 <= u < cam.W and 0 <= v < cam.H):
        return None
    return [int(round(1000 * u / cam.W)), int(round(1000 * v / cam.H))]


def rot_bin(cam, p, c, half: float = 0.02):
    a = to_px(cam, np.asarray(p) - half * np.asarray(c))
    b = to_px(cam, np.asarray(p) + half * np.asarray(c))
    if a is None or b is None:
        return None, None
    du, dv = (b[0] - a[0]) * cam.W / 1000.0, (b[1] - a[1]) * cam.H / 1000.0
    deg = math.degrees(math.atan2(dv, du)) % 180.0
    return round(deg, 1), int(deg // 15.0) % 12


def approach_family(a, p_world) -> str:
    from ..l9.grasp9 import family
    return family(np.asarray(a, float), np.asarray(p_world, float))


# ------------------------------------------------------------------------------------------------ judges
def judge_joint(J: dict, q_end: float, judge: dict, goal: float | None) -> dict:
    hi = float(J["hi"])
    share = q_end / hi if J["type"] == "prismatic" or J["kind"] == "door" else None
    ok = True
    why = []
    if "min_share" in judge:
        ok &= share is not None and share >= judge["min_share"]
        why.append(f"share {share:.2f} >= {judge['min_share']}")
    if "max_share" in judge:
        ok &= share is not None and share <= judge["max_share"]
        why.append(f"share {share:.2f} <= {judge['max_share']}")
    if "band" in judge:
        lo, hi_ = judge["band"]
        ok &= share is not None and lo <= share <= hi_
        why.append(f"share {share:.2f} in {judge['band']}")
    if "tol_deg" in judge and goal is not None:
        err = abs(math.degrees(q_end - goal))
        ok &= err <= judge["tol_deg"]
        why.append(f"angle err {err:.1f} deg <= {judge['tol_deg']}")
    return {"ok": bool(ok), "share": None if share is None else round(share, 3), "q": round(q_end, 4),
            "why": "; ".join(why)}


def judge_push(start_xy, end_xy, goal_xy, tilt_deg: float, judge: dict) -> dict:
    err = float(np.linalg.norm(np.asarray(end_xy) - np.asarray(goal_xy)))
    moved = float(np.linalg.norm(np.asarray(end_xy) - np.asarray(start_xy)))
    ok = err <= judge["pos_tol"] and tilt_deg <= judge["max_tilt_deg"]
    return {"ok": bool(ok), "err_m": round(err, 4), "moved_m": round(moved, 4), "tilt_deg": round(tilt_deg, 1)}
