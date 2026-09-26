"""Scripted low-level executor of the Astra-solo arm (no VLA): each command becomes one straight-line TCP move with a
minimum-jerk time profile (zero velocity and acceleration at both ends; duration = distance / V_AVG, at least MIN_T;
peak speed 1.875 x V_AVG), then the gripper action (close 0.6 s / open 0.5 s). IK, joint-step clamp and gravity
offset are the world's (world_isaac: OraclePlanner._ik). The workspace box and settle / blocked rules are the probe's
(harvest/astra_motion/executor.py): clip_box, REACH_TOL_M, settled = < 0.3 mm per tick for 4 ticks at the command,
blocked = settled farther than 3 cm or past duration + 2 s (reported as timeout).
Relative edits start from the commanded reference (pitfall P41: the arm sags ~1 cm under load), re-anchored to the
measured TCP when the two are more than 3 cm apart.
"""
from __future__ import annotations

import numpy as np

from ..astra_motion.executor import (BLOCKED_M, CLOSE_WAIT_S, OPEN_WAIT_S, REACH_TOL_M, SETTLE_M_PER_TICK,
                                     SETTLE_TICKS, clip_box)

V_AVG = 0.08  # m/s average along a move (peak 0.15 m/s; the oracle planner uses 0.06-0.20 m/s by phase)
MIN_T = 0.5  # s
EXTRA_S = 2.0  # s past the planned duration before a move counts as blocked


def min_jerk(s: float) -> float:
    s = min(max(s, 0.0), 1.0)
    return 10 * s ** 3 - 15 * s ** 4 + 6 * s ** 5


class MinJerkExec:
    def __init__(self, dt: float, table_z: float, tcp0, w_open: float, w_close: float, v_avg: float = V_AVG,
                 quat0=(1.0, 0.0, 0.0, 0.0)):
        self.dt, self.table_z, self.v_avg = dt, table_z, v_avg
        self.cmd = np.asarray(tcp0, float).copy()
        self.target = self.cmd.copy()  # the commanded reference (relative edits integrate on it)
        self.w_open, self.w_close, self.width = w_open, w_close, w_open
        self.quat0 = np.asarray(quat0, float)
        self.goal_quat = self.quat0.copy()
        self.seg = None  # (start, end, t0, T, grip)
        self.pending_grip = None  # (action, t) when the grip acts in place
        self.wait_until = self.wait_action = None
        self._still = 0
        self._last_tcp = None

    @property
    def busy(self) -> bool:
        return bool(self.seg is not None or self.wait_until is not None or self.pending_grip is not None)

    def go_to(self, pos, grip: str, t: float) -> list:
        """Absolute TCP target (clipped to the box). Returns clip events."""
        q, c = clip_box(pos, self.table_z)
        ev = [{"t": round(t, 3), "event": "clipped", "want": np.round(np.asarray(pos, float), 4).tolist(),
               "got": np.round(q, 4).tolist()}] if c else []
        d = float(np.linalg.norm(q - self.cmd))
        self.target = q.copy()
        self.seg = (self.cmd.copy(), q, t, max(d / self.v_avg, MIN_T), grip)
        self._still = 0
        return ev

    def move_by(self, delta, grip: str, t: float, tcp) -> list:
        tcp = np.asarray(tcp, float)
        base = self.target if np.linalg.norm(self.target - tcp) <= 0.03 else tcp
        return self.go_to(base + np.asarray(delta, float), grip, t)

    def grip(self, action: str, t: float) -> None:
        self.pending_grip = (action, t)

    def _act(self, action: str, t: float, tcp) -> list:
        self.width = self.w_close if action == "close" else self.w_open
        self.wait_until, self.wait_action = t + (CLOSE_WAIT_S if action == "close" else OPEN_WAIT_S), action
        return [{"t": round(t, 3), "event": action, "tcp": np.round(np.asarray(tcp, float), 4).tolist()}]

    def tick(self, t: float, tcp):
        """-> (commanded TCP position, gripper width, events)."""
        tcp = np.asarray(tcp, float)
        ev = []
        if self.wait_until is not None:
            if t >= self.wait_until - 1e-9:
                ev.append({"t": round(t, 3), "event": "gripper_done", "action": self.wait_action})
                self.wait_until = self.wait_action = None
            return self.cmd.copy(), self.width, ev
        if self.pending_grip is not None:
            a, _ = self.pending_grip
            self.pending_grip = None
            return self.cmd.copy(), self.width, self._act(a, t, tcp)
        if self.seg is None:
            return self.cmd.copy(), self.width, ev
        p0, p1, t0, T, g = self.seg
        s = (t + self.dt - t0) / T
        self.cmd = p0 + (p1 - p0) * min_jerk(s)
        at_cmd = s >= 1.0
        err = float(np.linalg.norm(tcp - p1))
        moved = float(np.linalg.norm(tcp - self._last_tcp)) if self._last_tcp is not None else 1.0
        self._last_tcp = tcp.copy()
        self._still = self._still + 1 if (at_cmd and moved < SETTLE_M_PER_TICK) else 0
        settled = self._still >= SETTLE_TICKS
        if at_cmd and (err < REACH_TOL_M or settled or t > t0 + T + EXTRA_S):
            kind = "reach" if err < REACH_TOL_M else ("settled" if settled and err <= BLOCKED_M else "timeout")
            ev.append({"t": round(t, 3), "event": kind, "err_mm": round(err * 1e3, 1)})
            self.seg = None
            if g in ("open", "close"):
                ev += self._act(g, t, tcp)
        return self.cmd.copy(), self.width, ev
