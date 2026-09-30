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
(goal_cmd' = true point + offset, an upper error) relabelled by the SAME truth rule (truth.mode_chunk)."""
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


LABEL_OF = {"A": "A", "B": "P", "C": "P", "A1": "A1", "A2": "A2"}  # training label per envelope rule (change 3)


def use_mode(s: dict, mode: str) -> dict:
    """The sample with the training label of envelope rule `mode`: A (hard clip) learns the clipped chunk, B / C learn
    'P' (straight to the true point; the code blends it with the upper's attraction). cmd_mismatch = |true - goal| >
    R_GOAL for every rule."""
    lab = (s.get("labels") or {}).get(LABEL_OF[mode])
    if lab is None or isinstance(lab, dict):  # rule-1/2 records (pre change 3): relabel first (tools/jcr/relabel.py)
        raise ValueError("sample without change-3 labels")
    out = dict(s)
    out.update(chunk=lab, mode=mode)
    return out


def branch(s: dict, rng, near_frac: float = 0.5, mode: str = "A") -> dict:
    """A forced-command copy of sample s: the command moved off the true point (an upper error), offset direction
    uniform (z halved), magnitude log-uniform 3 mm - 2 cm (near_frac) or 2 - 6 cm, relabelled by the same truth rule
    (A: the clipped chunk to the new command; B / C: 'P' is unchanged -- the true point did not move)."""
    d = rng.normal(size=3)
    d[2] *= 0.5
    d /= max(np.linalg.norm(d), 1e-9)
    lo, hi = (0.003, 0.02) if rng.uniform() < near_frac else (0.02, 0.06)
    m = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
    gt = np.asarray(s["goal_true"], float)
    g = gt + m * d
    out = dict(s)
    lab = LABEL_OF[mode]
    if lab != "P":
        out["chunk"] = T.mode_chunk(lab, s["p_cmd"], s["v"], gt, g, stop=bool(s.get("stop"))).tolist()
    an = set(s.get("anomaly", ())) - {"cmd_mismatch"}
    if T.mismatch(gt, g):
        an.add("cmd_mismatch")
    out.update(goal_cmd=g.tolist(), grip_event="keep", grip_row=None, anomaly=sorted(an),
               branch={"offset_m": round(m, 4)})
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
