"""Smooth application of Astra edits (spec §11, plan ruling 5): an edit enters as extra motion whose accumulated
displacement is weight x delta (6-D: tip translation m, rotation vector rad, robot frame). Inside the validity window
(= expected next answer, clamped to [ramp_min_s, ramp_max_s]) the remaining displacement is spread linearly over the
remaining window (GPT-as-Policy edit alpha = (i + 1) / steps), braking so that it lands (speed <= sqrt(2 a d)).
Limits: tip speed v_max / acceleration a_max, rotation w_max / alpha_max (no jumps). After the window with a rest
left (rate-limited), the speed decays to 0 over decay_s and the rest is dropped (logged). reset (a flipped answer)
empties the remaining displacement and brakes at a_max; scale_remaining (VLA fast check) shrinks it.

Authority a in [0, 1] (canon §84 supplement 8, E-SR1c ADOPT_C1; plan Task 17): step(..., authority=a) multiplies
the COMMANDED velocity by a before the acceleration / rate limit, and the remaining displacement is reduced only by
what is actually applied (the plan is never mutated by a). Why this form is jump-free: the applied velocity moves
toward a x v_des by at most a_max x dt per tick, and |a x v_des| <= v_max, so |v| <= v_max and |dv / dt| <= a_max
hold for every a sequence -- an immediate drop of a (Hysteresis decreases are immediate) brakes at a_max (at most
v^2 / (2 a_max) = 1 cm of further travel from v_max 0.08 m/s) instead of stopping in one tick, and a returning to 1
resumes the kept plan through the same acceleration limit. Scaling the OUTPUT displacement instead would turn an
immediate drop of a into a one-tick stop (deceleration v / dt = 8 m/s^2 >> a_max). a = 0 for the whole window ->
the velocity stays exactly 0 and the rest is dropped at the window end (the external command has zero effect).
The §6 decision projection (canon §84 supplement 8) is NOT implemented here (no task in this plan)."""
from __future__ import annotations

import math

import numpy as np


def _r(x):
    return [round(float(v), 5) for v in x]


class OffsetApplier:
    def __init__(self, p):
        self.p = p
        self.key, self.w, self.vec = None, 0.0, np.zeros(6)
        self.rem, self.v, self.applied, self.dropped = np.zeros(6), np.zeros(6), np.zeros(6), np.zeros(6)
        self.applied_abs = np.zeros(6)  # per-axis sum of |applied step| (the signed net is `applied`)
        self.t_end = -math.inf
        self._decay = {}
        self.v_seen, self.a_seen = 0.0, 0.0
        self.n = {"commands": 0, "resets": 0, "scaled": 0}
        self.log = []

    @property
    def active(self) -> bool:
        return bool(np.linalg.norm(self.rem) > 1e-9 or np.linalg.norm(self.v) > 1e-9)

    def direction(self):
        d = self.rem[:3] if np.linalg.norm(self.rem[:3]) > 1e-6 else self.v[:3]
        n = float(np.linalg.norm(d))
        return d / n if n > 1e-9 else None

    def command(self, key, vec6, weight: float, now: float, window_s: float) -> None:
        vec6 = np.asarray(vec6, float)
        if key == self.key:
            self.rem = self.rem + (weight - self.w) * self.vec
        else:
            self.key, self.vec, self.rem = key, vec6.copy(), weight * vec6
        self.w = float(weight)
        self.t_end = now + min(max(float(window_s), self.p.ramp_min_s), self.p.ramp_max_s)
        self._decay = {}
        self.n["commands"] += 1
        self.log.append({"t": round(now, 3), "event": "command", "key": key, "weight": self.w, "rem": _r(self.rem),
                         "t_end": round(self.t_end, 3)})

    def reset(self, now: float, reason: str) -> None:
        self.log.append({"t": round(now, 3), "event": "reset", "reason": reason, "dropped": _r(self.rem)})
        self.dropped += np.abs(self.rem)
        self.rem, self.key, self.w = np.zeros(6), None, 0.0
        self.n["resets"] += 1

    def scale_remaining(self, factor: float, now: float, reason: str) -> None:
        self.dropped += np.abs(self.rem) * (1.0 - factor)
        self.rem = self.rem * factor
        self.n["scaled"] += 1
        self.log.append({"t": round(now, 3), "event": "scale", "reason": reason, "factor": factor,
                         "rem": _r(self.rem)})

    def step(self, now: float, dt: float, authority: float = 1.0) -> np.ndarray:
        in_win = now < self.t_end - 1e-9
        k = min(1.0, max(0.0, float(authority)))
        out, v_new = np.zeros(6), self.v.copy()
        capped = False
        for i0, vmax, amax in ((0, self.p.v_max, self.p.a_max), (3, self.p.w_max, self.p.alpha_max)):
            sl = slice(i0, i0 + 3)
            rem, v = self.rem[sl].copy(), self.v[sl].copy()
            n = float(np.linalg.norm(rem))
            if in_win and n > 1e-12:
                speed = min(n / max(self.t_end - now, dt), vmax, math.sqrt(2.0 * amax * n))
                v_des, lim = rem / n * (speed * k), amax * dt  # authority on the command, before the limit
            elif n > 1e-12:  # window over with a rest: decay over decay_s
                if i0 not in self._decay:
                    self._decay[i0] = max(float(np.linalg.norm(v)) / self.p.decay_s, 1e-6)
                v_des, lim = np.zeros(3), self._decay[i0] * dt
            else:  # nothing left (reset): brake at the acceleration cap
                v_des, lim = np.zeros(3), amax * dt
            dv = v_des - v
            nd = float(np.linalg.norm(dv))
            if nd > lim:
                dv = dv * (lim / nd)
            vn = v + dv
            d = vn * dt
            if n > 1e-12:
                u = rem / n
                along = float(d @ u)
                if along > n:  # landing: never pass the remaining displacement, stop there (no drift after)
                    d, vn, capped = d * (n / along), np.zeros(3), True
                rem = rem - d
                if float(rem @ u) <= 1e-12:
                    rem = np.zeros(3)
            out[sl], v_new[sl], self.rem[sl] = d, vn, rem
        if not capped:
            self.a_seen = max(self.a_seen, float(np.linalg.norm(v_new[:3] - self.v[:3])) / dt)
        self.v_seen = max(self.v_seen, float(np.linalg.norm(v_new[:3])))
        self.v = v_new
        self.applied += out
        self.applied_abs += np.abs(out)
        if not in_win and np.linalg.norm(self.v) < 1e-9 and np.linalg.norm(self.rem) > 0:
            self.log.append({"t": round(now, 3), "event": "drop", "rest": _r(self.rem)})
            self.dropped += np.abs(self.rem)
            self.rem = np.zeros(6)
        if np.linalg.norm(self.v) < 1e-9:
            self.v = np.zeros(6)
        return out

    def state_json(self) -> dict:
        return {"key": self.key, "weight": self.w, "remaining_m": _r(self.rem[:3]), "remaining_rad": _r(self.rem[3:]),
                "velocity_mps": _r(self.v[:3])}

    def stats(self) -> dict:
        return {"applied_m": _r(self.applied[:3]), "applied_rad": _r(self.applied[3:]),
                "applied_abs_m": _r(self.applied_abs[:3]), "applied_abs_rad": _r(self.applied_abs[3:]),
                "dropped_m": round(float(np.linalg.norm(self.dropped[:3])), 5), "v_max_seen": round(self.v_seen, 5),
                "a_max_seen": round(self.a_seen, 5), **self.n}
