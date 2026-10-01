"""E-JV1 arm B text interface (docs/stage3/prereg_jv1.md §2): the small VLM reads and writes SPACE AS TEXT, like the
upper's method D -- a point on the head image (0-1000 x right / y down, Qwen-VL convention) + a height above the
table top (mm) -- and the rule controller turns the point back into xyz (pixel ray x the horizontal plane at that
height; no depth needed). Pure numpy.

Input text (prompt): the adapter command (destination point + height, allowed gripper action, stage, pull strength,
command age) and the robot state (TCP point + height, commanded-minus-measured TCP mm, commanded TCP velocity mm/s,
pad gap mm, gripper effort, 7 joints) -- the same information as JCR's cond vector (features.cond_vec).
Answer text: "<x> <y> <h> <event> <contact> <anomaly bits>", e.g. "512 433 175 k 0 00000"
  x y h   = the waypoint the hand should head for now (label 'P': the true task point; label 'A': the true point
            clipped to the 3 cm ball around the command = JCR1-0A's rule), the controller handles via-above / braking
  event   = k (keep) | c<r> (close at row r) | o<r> (open at row r) | s (stop: decelerate and hold)
  contact = 1 / 0 (pads touching the target), anomaly bits = truth.ANOMALIES order."""
from __future__ import annotations

import re

import numpy as np

from ..jcr import features as FT
from ..jcr import truth as T

TABLE_Z = 0.85  # = sim.scene.TABLE_TOP_Z (the world's table top)
SCALE = 1000.0
# head camera of the JCR world (calls/c000/cams.json of d1: identical for all 2,000 episodes, std 1e-15)
HEAD = {"W": 672, "H": 376, "fx": 367.0, "fy": 367.0, "cx": 336.0, "cy": 188.0,
        "R": [[-1.2377886312744702e-05, -0.6377792320884886, 0.7702192226654733],
              [-0.9999999998725613, 1.2829936464054318e-07, -1.59643634942748e-05],
              [1.0082920853258164e-05, -0.7702192227649226, -0.637779232008799]],
        "t": [0.10506324772111575, 0.02498161892797755, 1.4047340504674148]}
_R = np.asarray(HEAD["R"], float)
_t = np.asarray(HEAD["t"], float)
EV_RE = re.compile(r"^(k|s|c\d+|o\d+)$")


def cam_matches(cam, tol: float = 1e-6) -> bool:
    """True when a live geometry.Cam is the constant HEAD (the executor checks it once per episode)."""
    return (int(cam.W) == HEAD["W"] and int(cam.H) == HEAD["H"] and abs(cam.fx - HEAD["fx"]) < tol
            and np.allclose(np.asarray(cam.R, float), _R, atol=tol) and np.allclose(np.asarray(cam.t, float), _t,
                                                                               atol=tol))


def to_pt(p) -> tuple:
    """xyz (base frame) -> (x, y, h): 0-1000 head-image coordinates of its projection (continuous image coordinates,
    may leave 0-1000) and the height above the table top in mm, all rounded to int."""
    pc = _R.T @ (np.asarray(p, float) - _t)
    u = HEAD["fx"] * pc[0] / pc[2] + HEAD["cx"]
    v = HEAD["fy"] * pc[1] / pc[2] + HEAD["cy"]
    return (int(round(u / HEAD["W"] * SCALE)), int(round(v / HEAD["H"] * SCALE)),
            int(round((float(p[2]) - TABLE_Z) * 1000.0)))


def from_pt(x, y, h) -> np.ndarray:
    """(x, y, h) -> xyz: the head-camera ray through the image point meets the plane z = table + h."""
    u, v = float(x) / SCALE * HEAD["W"], float(y) / SCALE * HEAD["H"]
    d = _R @ np.array([(u - HEAD["cx"]) / HEAD["fx"], (v - HEAD["cy"]) / HEAD["fy"], 1.0])
    z = TABLE_Z + float(h) / 1000.0
    if abs(d[2]) < 1e-9:
        return _t + d
    return _t + d * ((z - _t[2]) / d[2])


def waypoint(s: dict, label: str = "P") -> np.ndarray:
    """The waypoint label of a sample: P = the true task point, A = it clipped to the 3 cm ball (JCR1-0A's rule);
    stop -> the commanded TCP (the controller decelerates and holds)."""
    if s.get("stop"):
        return np.asarray(s["p_cmd"], float)
    if label == "A":
        return T.project_ball(s["goal_true"], s["goal_cmd"], T.R_GOAL)[0]
    return np.asarray(s["goal_true"], float)


def rows(s: dict, c, stop: bool = False) -> np.ndarray:
    """The rule controller: H commanded-TCP rows (20 Hz) from the commanded TCP / velocity toward waypoint c
    (truth.smooth_chunk: speed <= V_MAX, acceleration <= A_MAX, via-above, braking without overshoot)."""
    return T.smooth_chunk(s["p_cmd"], s["v"], np.asarray(c, float), stop=stop)[0]


def _pt(p) -> str:
    x, y, h = to_pt(p)
    return f"point {x} {y} height {h}"


def prompt(s: dict) -> str:
    tcp, pc = np.asarray(s["tcp"], float), np.asarray(s["p_cmd"], float)
    off = np.round((pc - tcp) * 1000).astype(int)
    v = np.round(np.asarray(s["v"], float) * 1000).astype(int)
    q = " ".join(f"{a:.2f}" for a in (s.get("q") or [0.0] * 7)[:7])
    allow = s.get("allow") or "none"
    return (f"command: {_pt(s['goal_cmd'])}; gripper allowed {allow}; stage {s.get('height', 'lift')}; "
            f"pull {float(s.get('kappa', 1.0)):.1f}; age {min(float(s.get('cmd_age', 0.0)), 9.9):.1f} s\n"
            f"tcp: {_pt(tcp)}; commanded offset mm {off[0]} {off[1]} {off[2]}; velocity mm/s {v[0]} {v[1]} {v[2]}; "
            f"gap mm {int(round(float(s.get('grip_w', 0.0)) * 1000))}; effort {float(s.get('effort', 0.0)):.1f}\n"
            f"joints: {q}\n"
            "Answer: waypoint x y height, event, contact, anomaly bits.")


def event_code(c: int) -> str:
    kind, r = FT.decode_event(int(c))
    return {"keep": "k", "stop": "s"}.get(kind) or f"{kind[0]}{r}"


def answer(s: dict, label: str = "P") -> str:
    x, y, h = to_pt(waypoint(s, label))
    an = FT.anomaly_vec(s)[:len(T.ANOMALIES)]
    bits = "".join(str(int(b)) for b in an)
    return f"{x} {y} {h} {event_code(FT.event_class(s))} {int(bool(s.get('contact')))} {bits}"


def parse(text: str):
    """-> {"pt": (x, y, h), "event": class, "contact": 0/1, "anom": [bits]} or None (malformed)."""
    p = text.strip().split()
    if len(p) != 6 or not EV_RE.match(p[3]) or not re.fullmatch(r"[01]", p[4]) or \
            not re.fullmatch(r"[01]{%d}" % len(T.ANOMALIES), p[5]):
        return None
    try:
        x, y, h = int(p[0]), int(p[1]), int(p[2])
    except ValueError:
        return None
    e = p[3]
    if e == "k":
        ev = FT.EV_KEEP
    elif e == "s":
        ev = FT.EV_STOP
    else:
        r = int(e[1:])
        if r >= T.H:
            return None
        ev = 1 + r if e[0] == "c" else 1 + T.H + r
    return {"pt": (x, y, h), "event": ev, "contact": int(p[4]), "anom": [int(b) for b in p[5]]}
