"""JCR inputs / targets shared by training, serving and the closed-loop executor (docs/stage3/jcr_design.md §0-2, §3).
Pure numpy. A 'sample' is one 0.2 s decision (harvest.jcr.record samples.jsonl row, or the executor's live state).

cond vector (COND_DIM): joystick j = goal_cmd - tcp (fixed world/torso axes, m, x10), |j| (x10), log(|j| + 1 mm),
unit(j), p_cmd - tcp (x10; the commanded-vs-measured offset = load sag / lag), v (commanded TCP velocity, m/s x10),
envelope radius (x10), allowed gripper action one-hot (none / close / open), command age (s, clipped to 3, /3),
7 arm joints, pad gap (x10), gripper effort (/10), adapter pull strength kappa, stage one-hot (height intent above /
grasp / place / lift; NOW.md §1-0e).
Action target: the truth chunk as cumulative TCP displacement from the commanded TCP, [H, 3], normalized per
(row, axis) by the std of REAL samples (branches excluded, E-SR1c rule).
Event target: one class of 2H + 2 = keep | close@row r | open@row r | stop.
Anomaly target: ANOMALIES multi-hot (+ any). Branch = the same observation with a forced command
(goal_cmd' = tcp + offset) relabelled by the SAME truth rule (truth.project_ball + smooth_chunk)."""
from __future__ import annotations

import numpy as np

from . import truth as T

ALLOW = (None, "close", "open")
STAGES = ("above", "grasp", "place", "lift")
COND_DIM = 33
N_EVENT = 2 * T.H + 2  # keep, close@0..H-1, open@0..H-1, stop
EV_KEEP, EV_STOP = 0, 2 * T.H + 1
ANOM = T.ANOMALIES


def cond_vec(s: dict) -> np.ndarray:
    tcp = np.asarray(s["tcp"], float)
    j = np.asarray(s["goal_cmd"], float) - tcp
    n = float(np.linalg.norm(j))
    u = j / n if n > 1e-9 else np.zeros(3)
    a = np.zeros(3)
    a[ALLOW.index(s.get("allow"))] = 1.0
    q = np.asarray(s.get("q") or np.zeros(7), float)[:7]
    x = np.concatenate([10 * j, [10 * n, np.log(n + 1e-3)], u, 10 * (np.asarray(s["p_cmd"], float) - tcp),
                        10 * np.asarray(s["v"], float), [10 * float(s.get("r_goal", T.R_GOAL))], a,
                        [min(float(s.get("cmd_age", 0.0)), 3.0) / 3.0], q,
                        [10 * float(s.get("grip_w", 0.0)), float(s.get("effort", 0.0)) / 10.0],
                        [float(s.get("kappa", 1.0))], [float(s.get("height", "lift") == h) for h in STAGES]])
    assert x.shape == (COND_DIM,), x.shape
    return x.astype(np.float32)


def delta(s: dict) -> np.ndarray:
    return np.asarray(s["chunk"], float) - np.asarray(s["p_cmd"], float)[None]


def event_class(s: dict) -> int:
    if s.get("stop"):
        return EV_STOP
    e, r = s.get("grip_event", "keep"), s.get("grip_row")
    if e == "close" and r is not None:
        return 1 + int(r)
    if e == "open" and r is not None:
        return 1 + T.H + int(r)
    return EV_KEEP


def decode_event(c: int):
    """class -> (kind keep|close|open|stop, row or None)."""
    if c == EV_KEEP:
        return "keep", None
    if c == EV_STOP:
        return "stop", None
    if c <= T.H:
        return "close", c - 1
    return "open", c - 1 - T.H


def anomaly_vec(s: dict) -> np.ndarray:
    a = set(s.get("anomaly", ()))
    v = [float(k in a) for k in ANOM]
    return np.asarray(v + [float(bool(a))], np.float32)


def use_mode(s: dict, mode: str) -> dict:
    """The sample with the chunk / c* / cmd_mismatch of envelope rule `mode` (samples carry all three, record.py)."""
    lab = (s.get("labels") or {}).get(mode)
    if lab is None:
        return s
    out = dict(s)
    an = set(s.get("anomaly", ())) - {"cmd_mismatch"}
    if lab["mismatch"]:
        an.add("cmd_mismatch")
    out.update(chunk=lab["chunk"], c_star=lab["c_star"], anomaly=sorted(an), mode=mode)
    return out


def branch(s: dict, rng, near_frac: float = 0.5, mode: str = "A") -> dict:
    """A forced-joystick copy of sample s relabelled by the truth rule. Offset direction uniform (z halved), magnitude
    log-uniform 3 mm - 2 cm (near, near_frac) or 2 - 8 cm (far)."""
    tcp = np.asarray(s["tcp"], float)
    d = rng.normal(size=3)
    d[2] *= 0.5
    d /= max(np.linalg.norm(d), 1e-9)
    lo, hi = (0.003, 0.02) if rng.uniform() < near_frac else (0.02, 0.08)
    m = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
    g = tcp + m * d
    from .adapter import kappa
    kap = kappa(s.get("height", "lift"), bool(s.get("holding")), m) if "height" in s else float(s.get("kappa", 1.0))
    c, mis = T.target_point(mode, s["goal_true"], g, kap)
    stop = bool(s.get("stop"))
    P, _ = T.smooth_chunk(np.asarray(s["p_cmd"], float), np.asarray(s["v"], float), c, stop=stop)
    out = dict(s)
    an = set(s.get("anomaly", ())) - {"cmd_mismatch"}
    if mis:
        an.add("cmd_mismatch")
    out.update(goal_cmd=g.tolist(), c_star=c.tolist(), chunk=P.tolist(), grip_event="keep", grip_row=None, kappa=kap,
               anomaly=sorted(an), branch={"offset_m": round(m, 4)})
    return out


class Norm:
    """Per (row, axis) std of the real-sample delta targets (+ a floor)."""

    def __init__(self, std):
        self.std = np.maximum(np.asarray(std, float), 1e-4)

    @classmethod
    def fit(cls, samples):
        D = np.stack([delta(s) for s in samples])
        return cls(D.std(0))

    def z(self, d):
        return (np.asarray(d, float) / self.std).astype(np.float32)

    def unz(self, z):
        return np.asarray(z, float) * self.std

    def to_json(self):
        return {"std": self.std.tolist()}
