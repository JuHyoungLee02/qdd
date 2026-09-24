"""P: robot-side predicates from proprioception only (D28 §3.0, canon §61): gripper width, gripper effort (current),
TCP height from FK, and the arm joint effort residual against the gravity torque of the current pose.

  gripper_open   = width >= th_w
  holding_t      = th_lo < width < GRIP_OPEN_M  and  grip_tau >= th_I
  lifted_holding = holding rule  and  tcp_z >= th_z
  contact_stall  = width >= th_w  and  tau_res >= th_tau          (open-hand collision)

Thresholds are fit on calibration data by grid search maximizing balanced accuracy. scores() maps the signed
normalized margin of each rule (min over its conjunction) to [0, 1] with 0.5 + 0.5 tanh(m): >= 0.5 iff the rule fires.
"""
from __future__ import annotations

import numpy as np

from ..predicates import GRIP_OPEN_M
from .metrics import ba_from_counts, counts

ROBOT = ("gripper_open", "holding_t", "lifted_holding", "contact_stall")
NOISE_FRAC = 0.02  # [assumption] current-sensing noise sigma = 2 % of the joint effort limit


def noisy(tau, limits, seed: int, frac: float = NOISE_FRAC):
    tau = np.asarray(tau, float)
    rng = np.random.default_rng(seed)
    return tau + rng.normal(0.0, 1.0, tau.shape) * frac * np.asarray(limits, float)


def _ba(y, h):
    v = ba_from_counts(counts(y, h))
    return -1.0 if np.isnan(v) else v


def _grid(x, n=200):
    x = np.asarray(x, float)
    return np.unique(np.quantile(x, np.linspace(0, 1, n)))


def fit_threshold(x, y, direction: int = +1, base=None) -> float:
    """Threshold th of the rule (x >= th) for direction +1 or (x <= th) for -1, AND-ed with `base` (bool array)."""
    x, y = np.asarray(x, float), np.asarray(y, bool)
    b = np.ones_like(y) if base is None else np.asarray(base, bool)
    best, th_best = -2.0, None
    for th in _grid(x):
        h = b & ((x >= th) if direction > 0 else (x <= th))
        s = _ba(y, h)
        if s > best:
            best, th_best = s, float(th)
    return th_best


def fit(f: dict, t: dict) -> dict:
    w, g, z, r = (np.asarray(f[k], float) for k in ("width", "grip_tau", "tcp_z", "tau_res"))
    par = {"scale": {k: float(max(np.std(np.asarray(f[k], float)), 1e-6)) for k in ("width", "grip_tau", "tcp_z",
                                                                                       "tau_res")},
           "th_hi": GRIP_OPEN_M}
    par["th_w"] = fit_threshold(w, t["gripper_open"], +1)
    best = (-2.0, None, None)
    y = np.asarray(t["holding_t"], bool)
    for lo in _grid(w[w < GRIP_OPEN_M], 60):
        band = (w > lo) & (w < GRIP_OPEN_M)
        for gi in _grid(g, 60):
            s = _ba(y, band & (g >= gi))
            if s > best[0]:
                best = (s, float(lo), float(gi))
    par["th_lo"], par["th_I"] = best[1], best[2]
    hold = _hold(w, g, par)
    par["th_z"] = fit_threshold(z, t["lifted_holding"], +1, base=hold)
    par["th_tau"] = fit_threshold(r, t["contact_stall"], +1, base=w >= par["th_w"])
    return par


def _hold(w, g, par):
    return (w > par["th_lo"]) & (w < par["th_hi"]) & (g >= par["th_I"])


def apply(f: dict, par: dict) -> dict:
    w, g, z, r = (np.asarray(f[k], float) for k in ("width", "grip_tau", "tcp_z", "tau_res"))
    hold = _hold(w, g, par)
    return {"gripper_open": w >= par["th_w"], "holding_t": hold, "lifted_holding": hold & (z >= par["th_z"]),
            "contact_stall": (w >= par["th_w"]) & (r >= par["th_tau"])}


def scores(f: dict, par: dict) -> dict:
    s = par["scale"]
    w, g, z, r = (np.asarray(f[k], float) for k in ("width", "grip_tau", "tcp_z", "tau_res"))
    m_open = (w - par["th_w"]) / s["width"]
    m_hold = np.minimum.reduce([(w - par["th_lo"]) / s["width"], (par["th_hi"] - w) / s["width"],
                                (g - par["th_I"]) / s["grip_tau"]])
    # tie rule: exactly at a >= threshold counts as fired (margin 0 -> 0.5)
    m_lh = np.minimum(m_hold, (z - par["th_z"]) / s["tcp_z"])
    m_st = np.minimum(m_open, (r - par["th_tau"]) / s["tau_res"])
    sq = lambda m: 0.5 + 0.5 * np.tanh(m)  # noqa: E731
    out = {"gripper_open": sq(m_open), "holding_t": sq(m_hold), "lifted_holding": sq(m_lh),
           "contact_stall": sq(m_st)}
    # strict inequalities of the band (w > lo, w < hi) at exactly 0 margin do not fire: push below 0.5
    rule = apply(f, par)
    for k in out:
        out[k] = np.where(rule[k], np.maximum(out[k], 0.5), np.minimum(out[k], 0.5 - 1e-9))
    return out
