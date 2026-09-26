"""E-ACC snapshot bench (docs/stage3/prereg_eacc.md) -- pure parts (no Isaac, no model calls).

Episodes run in Isaac (tools/eacc/capture.py) with the R2 oracle planner as a stand-in "VLA":
  on     the oracle planner unchanged; one snapshot in a designated phase. The policy is on plan -> the right command
         is continue (stop once the task is complete at arrival; only stop in done).
  off_a  wrong spot: the approach goal is moved by delta (|delta| 7-10 cm, horizontal) and the planner stalls there
         (it never leaves approach) -- the policy heads for / hovers at a spot beside the target.
  off_b  wrong object: the approach goal is above another object (mug_tray -> the tray, mug_marker -> the marker,
         bottle_tray -> the mug) and the planner stalls there.
  off_c  wrong place: after the grasp the carry goal is moved by delta and the planner stalls there (holding).
  off_*: the right command is an edit towards the correct subgoal.
Snapshot: all three cameras (raw PNG) + camera models + tip + the last 3 s trace, and the whole episode path
(t, tip, phase, pad gap, holding) so every arm is scored at the same arrival state t_snap + L_ARR.

Oracle (object poses are read by the capture only for scoring; nothing of it enters a prompt):
  segment acceptable set: on = {segment at send, segment at arrival}; off_a / off_b = {approach}; off_c = {carry}
  expected command: on -> continue (+ stop when the snapshot already shows the release: open / retreat; done ->
  stop only); off -> edit
The stand-in policy runs at SPEED x the oracle planner's TCP speeds (the fused VLA of the E-Couple dry run moved
about 3-10 cm/s in approach against the planner's 20 cm/s, so a full-speed planner finishes the whole task within
one 9.3 s Astra call).
  edit direction at arrival: to the correct subgoal from the arrival tip -- off_a / off_b: the pre-grasp point (10 cm
  above the target top, the planner's approach goal) when the tip is at most 3 cm below that height, else the grasp
  point; off_c: horizontal to the place centre. Correct = angle < 60 deg (cos > 0.5, E-SR0 / probe_acc)."""
from __future__ import annotations

import math

import numpy as np

L_ARR = 9.3  # CoupleParams.latency_init_s (canon §86 supplement 2)
TRACE_S = 2.5  # CoupleParams.trace_s
APPROACH_ABOVE_TOP_M = 0.10  # = sim.planner.APPROACH_ABOVE_TOP_M
GRASP_BELOW_TOP_M = 0.018  # = sim.planner.GRASP_BELOW_TOP_M
CARRY_TCP_Z = 0.20  # = sim.planner.CARRY_TCP_Z (table frame)
DIR_OK_DEG = 60.0
SPEED = 0.5  # stand-in policy speed factor on the planner's V_FAST / V_SLOW / V_LIFT
RELEASED_PHASES = ("open", "retreat")
PHASE_SEGMENT = {"approach": "approach", "descend": "descend", "close": "grasp", "lift": "lift", "carry": "carry",
                 "place_descend": "place", "open": "release", "retreat": "retreat", "done": "done"}  # = intent.PHASE_SEGMENT
SEG_ORDER = ("approach", "descend", "grasp", "lift", "carry", "place", "release", "retreat", "done")
SEG_DO = {"grasp": "close", "release": "open"}
SNAP_AT = {"approach": 0.8, "descend": 0.8, "close": 0.3, "lift": 0.6, "carry": 0.8, "place_descend": 0.8,
           "open": 0.25, "retreat": 0.4, "done": 0.5}  # s into the phase for an 'on' snapshot
OFF_FRAC = 0.6  # 'off' snapshot: 60 % of the way from the phase start to the wrong goal
WRONG_OBJ = {"mug_tray": "o5", "mug_marker": "o11", "bottle_tray": "o3"}
AFTER_S = 26.0  # sim seconds recorded after the snapshot (arrival 9.3 s; effort medium latency up to ~25 s)
WRONG_X, WRONG_Y = (0.30, 0.58), (-0.48, 0.06)  # clamp box of a moved goal (about the distractor band, scene.py)

# ------------------------------------------------------------------------------------------ episode plan (fixed)
TASKS3 = ("mug_tray", "mug_marker", "bottle_tray")
ON_PHASES = ("approach", "descend", "close", "lift", "carry", "place_descend", "open", "retreat", "done", "done",
             "carry", "approach")


def plan() -> list:
    """The fixed episode list (id, kind, seed, task, on-phase). Per kind the first entries that pass the capture
    checks form the paid set (prereg §2); DEV seeds 0-29 only (P47)."""
    out = []
    for i, ph in enumerate(ON_PHASES):  # 12: 10 + 2 spare
        s = 6 + i
        out.append({"id": f"on_{i:02d}", "kind": "on", "seed": s, "task": TASKS3[i % 3], "phase": ph})
    for kind, base, n in (("off_a", 16, 9), ("off_b", 6, 9), ("off_c", 18, 12)):
        for i in range(n):
            s = (base + i) % 30
            out.append({"id": f"{kind}_{i:02d}", "kind": kind, "seed": s, "task": TASKS3[(i + 1) % 3], "phase": None})
    return out


def delta_for(ep_id: str, seed: int, tries: int = 8) -> list:
    """Horizontal goal shift |d| in [0.07, 0.10] m in a seeded direction (the capture rotates it by 90 deg when the
    moved goal leaves the clamp box -- rotate(k))."""
    rng = np.random.default_rng(abs(hash_id(ep_id)) % (2 ** 32) + seed)
    ang = float(rng.uniform(0, 2 * math.pi))
    mag = float(rng.uniform(0.07, 0.10))
    return [mag * math.cos(ang), mag * math.sin(ang), 0.0]


def rotate(d: list, k: int) -> list:
    c, s = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
    return [c * d[0] - s * d[1], s * d[0] + c * d[1], 0.0]


def in_box(p) -> bool:
    return WRONG_X[0] <= p[0] <= WRONG_X[1] and WRONG_Y[0] <= p[1] <= WRONG_Y[1]


def hash_id(s: str) -> int:
    h = 0
    for ch in s.encode():
        h = (h * 131 + ch) % 1000003
    return h


# ------------------------------------------------------------------------------------------ path helpers
def at(path: list, t: float) -> dict:
    """The recorded path row nearest to t (the last row after the end: the robot holds still once stalled/done)."""
    if t >= path[-1]["t"]:
        return path[-1]
    return min(path, key=lambda r: abs(r["t"] - t))


def phases_between(path: list, t0: float, t1: float) -> list:
    out = []
    for r in path:
        if t0 - 1e-9 <= r["t"] <= t1 + 1e-9 and (not out or out[-1] != r["phase"]):
            out.append(r["phase"])
    return out


def seg_triple(phase: str):
    now = PHASE_SEGMENT.get(phase)
    if now is None:
        return None
    i = SEG_ORDER.index(now)
    return {"now": now, "do": SEG_DO.get(now, "none"), "next": SEG_ORDER[i + 1] if i + 1 < len(SEG_ORDER) else "done"}


def angle_deg(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na < 1e-9 or nb < 1e-9:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b) / (na * nb)))))


# ------------------------------------------------------------------------------------------ oracle
def subgoal(meta: dict, tip) -> np.ndarray:
    o = meta["oracle"]
    tip = np.asarray(tip, float)
    if meta["kind"] == "off_c":
        p = np.asarray(o["place_xy"], float)
        return np.array([p[0], p[1], tip[2]])
    pre, gp = np.asarray(o["pregrasp"], float), np.asarray(o["grasp_point"], float)
    return pre if tip[2] >= pre[2] - 0.03 else gp


def oracle(meta: dict, horizon_s: float = L_ARR) -> dict:
    t = meta["t_snap"]
    path = meta["path"]
    ra = at(path, t + horizon_s)
    ph_s, ph_a = at(path, t)["phase"], ra["phase"]
    if meta["kind"] == "on":
        segs = {x["now"] for x in (seg_triple(ph_s), seg_triple(ph_a)) if x}
        cmds = {"stop"} if ph_s == "done" else ({"continue", "stop"} if ph_s in RELEASED_PHASES else {"continue"})
        return {"expected": sorted(cmds), "segments": sorted(segs), "phase_send": ph_s, "phase_arr": ph_a,
                "dir_arr": None, "dir_send": None}
    tip_s, tip_a = np.asarray(meta["tip"], float), np.asarray(ra["tip"], float)
    return {"expected": ["edit"], "segments": ["carry"] if meta["kind"] == "off_c" else ["approach"],
            "phase_send": ph_s, "phase_arr": ph_a,
            "dir_arr": (subgoal(meta, tip_a) - tip_a).round(4).tolist(),
            "dir_send": (subgoal(meta, tip_s) - tip_s).round(4).tolist()}


def score_answer(meta: dict, ans: dict | None, horizon_s: float = L_ARR) -> dict:
    """ans: None (invalid / API error) or {"command": gated command, "command_raw", "edit_dp", "segment"}.
    Invalid answers count as wrong on every metric (intention to treat)."""
    o = oracle(meta, horizon_s)
    out = {"kind": meta["kind"], "expected": o["expected"], "valid": ans is not None}
    if ans is None:
        out.update(cmd_ok=False, dir_ok=False if o["dir_arr"] else None, dir_ok_send=False if o["dir_arr"] else None,
                   seg_ok=False, triple_ok=False)
        return out
    out["cmd_ok"] = ans["command"] in o["expected"]
    out["cmd_raw_ok"] = ans.get("command_raw") in o["expected"]
    if o["dir_arr"] is not None:
        dp = ans.get("edit_dp") if ans["command"] == "edit" else None
        a_arr = angle_deg(dp, o["dir_arr"]) if dp is not None else None
        a_snd = angle_deg(dp, o["dir_send"]) if dp is not None else None
        out.update(ang_arr=None if a_arr is None else round(a_arr, 1), ang_send=None if a_snd is None else round(a_snd, 1),
                   dir_ok=a_arr is not None and a_arr < DIR_OK_DEG, dir_ok_send=a_snd is not None and a_snd < DIR_OK_DEG)
        dpr = ans.get("edit_dp_raw")
        a_raw = angle_deg(dpr, o["dir_arr"]) if dpr is not None else None
        out["dir_ok_raw"] = a_raw is not None and a_raw < DIR_OK_DEG  # before the gate (an edit the gate removed)
    seg = ans.get("segment")
    if seg is None:
        out.update(seg_ok=None, triple_ok=None)
    else:
        out["seg_ok"] = seg["now"] in o["segments"]
        exp = seg_triple({v: k for k, v in PHASE_SEGMENT.items()}[seg["now"]])
        out["triple_ok"] = out["seg_ok"] and seg["do"] == exp["do"] and seg["next"] == exp["next"]
    return out


# ------------------------------------------------------------------------------------------ request / images
MAG_BINS = (("tiny", 0.005), ("small", 0.01), ("medium", 0.02), ("large", 0.04), ("xlarge", 0.08))
MAG_CENTER_M = dict(MAG_BINS)  # = couple.driver.MAG_CENTER_M
_XY8 = ["plus_x", "plus_x_plus_y", "plus_y", "minus_x_plus_y", "minus_x", "minus_x_minus_y", "minus_y",
        "plus_x_minus_y"]


def committed_decision(p_now, p_next) -> dict:
    """= sim.planner.oracle_answer over one decision step (0.33 s), the VLA's committed joystick decision."""
    d = np.asarray(p_next, float) - np.asarray(p_now, float)
    h = math.hypot(d[0], d[1])
    dxy = "none_xy" if h < 0.0025 else _XY8[int(round(math.atan2(d[1], d[0]) / (math.pi / 4))) % 8]
    dz = "none_z" if abs(d[2]) < 0.0025 else ("up" if d[2] > 0 else "down")
    n = float(np.linalg.norm(d))
    logs = [abs(math.log(max(n, 1e-6)) - math.log(v)) for _, v in MAG_BINS]
    mag = MAG_BINS[int(np.argmin(logs))][0] if n >= 0.0025 else "tiny"
    return {"dir_xy": dxy, "dir_z": dz, "mag_coarse": mag}


_XY_SIGN = {"plus_x": (1, 0), "minus_x": (-1, 0), "plus_y": (0, 1), "minus_y": (0, -1), "plus_x_plus_y": (1, 1),
            "plus_x_minus_y": (1, -1), "minus_x_plus_y": (-1, 1), "minus_x_minus_y": (-1, -1), "none_xy": (0, 0)}
_Z_SIGN = {"up": 1, "down": -1, "none_z": 0}


def token_vec(committed: dict):
    """= couple.driver.next_motion_vec: the decision-token centre drawn by production v1 (F3)."""
    xy = _XY_SIGN.get(committed.get("dir_xy"))
    if xy is None:
        return None
    v = np.array([xy[0], xy[1], _Z_SIGN.get(committed.get("dir_z"), 0)], float)
    if not np.any(v):
        return None
    return v / float(np.linalg.norm(v)) * MAG_CENTER_M.get(committed.get("mag_coarse"), 0.0)


def predict_ee(trace: list, horizon: float, cap: float = 0.10) -> np.ndarray:
    """= couple.driver.predict_ee with no remaining correction; trace [(t, p)] of the last 0.5 s."""
    (t0, p0), (t1, p1) = trace[0], trace[-1]
    d = (np.asarray(p1) - np.asarray(p0)) / (t1 - t0) * horizon if t1 > t0 else np.zeros(3)
    n = float(np.linalg.norm(d))
    if n > cap:
        d = d * (cap / n)
    return np.asarray(p1, float) + d


def _r(x):
    return [round(float(v), 4) for v in x]


def vla_view(meta: dict) -> dict:
    t = meta["t_snap"]
    p_now = np.asarray(meta["tip"], float)
    committed = committed_decision(p_now, at(meta["path"], t + 1 / 3)["tip"])
    exec_vec = np.asarray(at(meta["path"], t + 0.5)["tip"], float) - p_now
    return {"committed": committed, "token_vec": token_vec(committed), "exec_vec": exec_vec}


def gripper_word(phase: str, grip_open: bool) -> str:
    return "closing" if phase == "close" else "opening" if phase == "open" else ("open" if grip_open else "closed")


def request(meta: dict, cams: list, *, version: str, next_vec, context: bool) -> dict:
    """The coupling request of the snapshot. v1 = the production field set (driver.request, F0); v2 adds
    since_last_request (canon §91) when context is on. next_motion_m = the arrow drawn (token centre in v1,
    executed chunk motion in v2)."""
    t = meta["t_snap"]
    path = meta["path"]
    ph = at(path, t)["phase"]
    tr = [(r["t"], np.asarray(r["tip"], float)) for r in path if t - 0.5 - 1e-9 <= r["t"] <= t + 1e-9]
    pred = predict_ee(tr, L_ARR) if len(tr) >= 2 else np.asarray(meta["tip"], float)
    grip_open = meta["grip_w"] > 0.08
    vv = vla_view(meta)
    req = {"schema": "astra-couple@v1" if version == "v1" else "astra-couple@v2-eacc", "mode": "F0", "request_no": 1,
           "t_state": round(t, 3), "task": meta["instruction"], "active_arm": "right", "cameras": list(cams),
           "tip_now_m": _r(meta["tip"]),
           "vla_now": {"stage": "S2" if meta["holding"] else "S1", "phase": ph, "committed": dict(sorted(vv["committed"].items())),
                       "next_motion_m": None if next_vec is None else _r(next_vec), "motion": None},
           "predicted_ee_at_arrival": {"pos_m": _r(pred), "horizon_s": L_ARR, "gripper": gripper_word(ph, grip_open),
                                       "method": "0.5 s tip velocity x horizon (capped) + remaining correction"},
           "events": []}
    if version != "v1" and context:
        t0 = t - L_ARR
        if t0 < 0:
            req["since_last_request"] = {"previous_request": None, "since_episode_start_s": round(t, 1),
                                         "vla_tip_moved_m": _r(np.asarray(meta["tip"]) - np.asarray(path[0]["tip"])),
                                         "vla_phases": phases_between(path, 0.0, t)}
        else:
            prev_ph = at(path, t0)["phase"]
            req["since_last_request"] = {"previous_request": {"age_s": L_ARR, "command": "continue",
                                                              "segment": seg_triple(prev_ph)},
                                         "vla_tip_moved_m": _r(np.asarray(meta["tip"]) - np.asarray(at(path, t0)["tip"])),
                                         "vla_phases": phases_between(path, t0, t)}
    return req


def trace_points(meta: dict) -> list:
    t = meta["t_snap"]
    return [np.asarray(r["tip"], float) for r in meta["path"] if t - TRACE_S - 1e-9 <= r["t"] <= t + 1e-9]


def cam_models(meta: dict) -> dict:
    """G1 v2 / capture camera json (fx, fy, cx, cy, R, t, W, H) -> couple.overlay.CamModel dicts by request name."""
    out = {}
    for name, c in meta["cams"].items():
        K = [[c["fx"], 0, c["cx"]], [0, c["fy"], c["cy"]], [0, 0, 1]]
        out[name] = {"K": K, "R": c["R"], "t": c["t"], "W": c["W"], "H": c["H"]}
    return out
