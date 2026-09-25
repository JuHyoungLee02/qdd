"""The code executor shared by every mode (the model never commands joints): a queue of TCP targets, each followed in
a straight line at a fixed TCP speed, then the target's gripper action. Orientation (top-down, the oracle's grasp
yaw) and IK are the world's (world_isaac: OraclePlanner._ik with its joint-step clamp and gravity offset).

Safety box (clip, counted as 'clipped'): x 0.25-0.65, y -0.50-0.10 (= runtime/skills.WS_X/WS_Y), TCP z from table
+ 2.5 cm (fingertips 22.5 mm below the TCP stay above the table) to table + 40 cm.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

SAFE_X, SAFE_Y, SAFE_DZ = (0.25, 0.65), (-0.50, 0.10), (0.025, 0.40)
V_TCP = 0.08  # m/s, every mode (the oracle uses 0.06-0.20 by phase)
A_MAX = 0.32  # m/s^2, smooth executor: 0 -> V_TCP in 0.25 s
REACH_TOL_M = 0.008
SETTLE_M_PER_TICK, SETTLE_TICKS = 0.0003, 4  # < 0.3 mm per tick for 4 ticks at the command = settled
BLOCKED_M = 0.03  # settled farther than this from the target = blocked (reported as a timeout, no 2 s wait)
CLOSE_WAIT_S, OPEN_WAIT_S = 0.6, 0.5  # = planner.CLOSE_WAIT_S / OPEN_WAIT_S


@dataclass
class Target:
    pos: np.ndarray
    grip: str = "keep"
    tag: str = ""
    meta: dict = field(default_factory=dict)


def clip_box(p, table_z: float):
    p = np.asarray(p, float)
    q = np.array([np.clip(p[0], *SAFE_X), np.clip(p[1], *SAFE_Y),
                  np.clip(p[2], table_z + SAFE_DZ[0], table_z + SAFE_DZ[1])])
    return q, bool(np.linalg.norm(q - p) > 1e-9)


class SmoothExec:
    """Smooth application of staggered answers (coupling spec §11, user-log 83): an edit's delta_position is applied as
    a linearly ramped offset over its validity window (until the next answer is expected, `window` s) -- i.e. a
    constant velocity scale * delta / window -- scaled by consensus (the harness passes 0.5 for a single answer,
    1.0 when two consecutive answers agree), decaying linearly to zero over `decay_s` when not refreshed, and reset to
    zero before a new ramp on a direction flip. A gripper action is done at the end of its window (motion stops,
    close 0.6 s / open 0.5 s). Speed never exceeds V_TCP."""

    def __init__(self, dt: float, table_z: float, tcp0, w_open: float, w_close: float, window: float = 1.0,
                 decay_s: float = 0.5, v_max: float = V_TCP, quat0=(1.0, 0.0, 0.0, 0.0)):
        self.dt, self.table_z, self.window, self.decay_s, self.v_max = dt, table_z, window, decay_s, v_max
        self.cmd = np.asarray(tcp0, float).copy()
        self.w_open, self.w_close, self.width = w_open, w_close, w_open
        self.quat0 = np.asarray(quat0, float)
        self.goal_quat = self.quat0.copy()
        self.v = np.zeros(3)
        self.v_tgt = np.zeros(3)
        self.t_end = -np.inf
        self.grip_at_end = None
        self.t_grip = np.inf
        self.wait_until = self.wait_action = None
        self._clipped = False

    rotate = None  # replaced by MotionExec.rotate at the end of this module

    def apply(self, dp_m, grip: str, t: float, scale: float, flip: bool, window: float | None = None) -> None:
        """window: the validity window of this answer (serial stream: the expected time until the next answer). With
        a gripper action the move is done quickly (|delta| / v_max, at least 0.5 s) and the action follows."""
        if flip:
            self.v = np.zeros(3)
        dp = scale * np.asarray(dp_m, float)
        w = self.window if window is None else float(window)
        if grip in ("open", "close"):
            w = max(float(np.linalg.norm(dp)) / self.v_max, 0.5)
        v = dp / w
        n = float(np.linalg.norm(v))
        self.v_tgt = v * (self.v_max / n) if n > self.v_max else v
        self.t_end = t + w
        if grip in ("open", "close") and grip != self.grip_at_end:
            # a repeated request keeps its first deadline (refreshes never postpone it); 'keep' leaves it pending
            self.grip_at_end, self.t_grip = grip, t + w

    @property
    def busy(self) -> bool:
        return bool(self.wait_until is not None or np.linalg.norm(self.v) > 1e-9 or self.grip_at_end)

    def tick(self, t: float, tcp):
        ev = []
        if self.wait_until is not None:
            if t >= self.wait_until - 1e-9:
                ev.append({"t": round(t, 3), "event": "gripper_done", "action": self.wait_action})
                self.wait_until = self.wait_action = None
            return self.cmd.copy(), self.width, ev
        if self.grip_at_end and t >= self.t_grip - 1e-9:
            g, self.grip_at_end = self.grip_at_end, None
            self.v = self.v_tgt = np.zeros(3)
            self.width = self.w_close if g == "close" else self.w_open
            self.wait_until, self.wait_action = t + (CLOSE_WAIT_S if g == "close" else OPEN_WAIT_S), g
            ev.append({"t": round(t, 3), "event": g, "tcp": np.round(np.asarray(tcp, float), 4).tolist()})
            return self.cmd.copy(), self.width, ev
        if t < self.t_end - 1e-9:
            v_des = self.v_tgt
        elif self.decay_s > 0 and t < self.t_end + self.decay_s:
            v_des = self.v_tgt * max(0.0, 1.0 - (t - self.t_end) / self.decay_s)
        else:
            v_des = np.zeros(3)
        dv = v_des - self.v  # velocity changes are acceleration-limited (no velocity steps)
        n = float(np.linalg.norm(dv))
        a = A_MAX * self.dt
        self.v = v_des.copy() if n <= a else self.v + dv * (a / n)
        q, c = clip_box(self.cmd + self.v * self.dt, self.table_z)
        if c and not self._clipped:
            ev.append({"t": round(t, 3), "event": "clipped"})
        self._clipped = c
        self.cmd = q
        return self.cmd.copy(), self.width, ev


class MotionExec:
    def __init__(self, dt: float, table_z: float, tcp0, w_open: float, w_close: float, v: float = V_TCP,
                 reach_tol: float = REACH_TOL_M, extra_s: float = 2.0, quat0=(1.0, 0.0, 0.0, 0.0)):
        self.dt, self.table_z, self.v, self.reach_tol, self.extra_s = dt, table_z, v, reach_tol, extra_s
        self.quat0 = np.asarray(quat0, float)
        self.goal_quat = self.quat0.copy()  # the world turns the gripper toward it (rate-limited)
        self.cmd = np.asarray(tcp0, float).copy()
        self.w_open, self.w_close, self.width = w_open, w_close, w_open
        self.queue: list = []
        self.cur = None
        self.wait_until = None
        self.wait_action = None
        self.deadline = None
        self.ref = self.cmd.copy()  # the last commanded target (relative commands integrate on it)
        self._still = 0
        self._last_tcp = None

    def clip(self, p):
        return clip_box(p, self.table_z)

    def load(self, targets, t: float) -> list:
        """Replace the pending targets (the running one is dropped too). Returns clip events."""
        self.queue, self.cur, ev = [], None, []
        for tg in targets:
            q, c = self.clip(tg.pos)
            if c:
                ev.append({"t": round(t, 3), "event": "clipped", "tag": tg.tag, "want": np.round(tg.pos, 4).tolist(),
                           "got": np.round(q, 4).tolist()})
            self.queue.append(Target(q, tg.grip, tg.tag, dict(tg.meta, clipped=c)))
        if self.queue:
            self.ref = self.queue[-1].pos.copy()
        return ev

    def base(self, tcp, max_gap: float = 0.03) -> np.ndarray:
        """Where a relative command starts: the commanded reference (so a steady lag under load does not swallow small
        corrections), re-anchored to the measured TCP when the two are more than max_gap apart (blocked arm)."""
        tcp = np.asarray(tcp, float)
        return self.ref.copy() if np.linalg.norm(self.ref - tcp) <= max_gap else tcp.copy()

    def rotate(self, rotvec) -> None:
        """Turn the goal orientation by a base-frame rotation vector (edit delta_rotation_rad)."""
        from .geometry import quat_from_rotvec, quat_mul
        q = quat_mul(quat_from_rotvec(rotvec), self.goal_quat)
        self.goal_quat = q / np.linalg.norm(q)

    @property
    def busy(self) -> bool:
        return bool(self.queue or self.cur is not None or self.wait_until is not None)

    def tick(self, t: float, tcp):
        """-> (commanded TCP position, gripper width, events)."""
        tcp = np.asarray(tcp, float)
        ev = []
        if self.wait_until is not None:
            if t >= self.wait_until - 1e-9:
                ev.append({"t": round(t, 3), "event": "gripper_done", "action": self.wait_action})
                self.wait_until = self.wait_action = None
            return self.cmd.copy(), self.width, ev
        if self.cur is None and self.queue:
            self.cur = self.queue.pop(0)
            self.deadline = t + float(np.linalg.norm(self.cur.pos - self.cmd)) / self.v + self.extra_s
        if self.cur is None:
            return self.cmd.copy(), self.width, ev
        d = self.cur.pos - self.cmd
        n = float(np.linalg.norm(d))
        step = self.v * self.dt
        self.cmd = self.cur.pos.copy() if n <= step else self.cmd + d * (step / n)
        err = float(np.linalg.norm(tcp - self.cur.pos))
        at_cmd = float(np.linalg.norm(self.cmd - self.cur.pos)) < 1e-9
        moved = float(np.linalg.norm(tcp - self._last_tcp)) if self._last_tcp is not None else 1.0
        self._last_tcp = tcp.copy()
        self._still = self._still + 1 if (at_cmd and moved < SETTLE_M_PER_TICK) else 0
        settled = self._still >= SETTLE_TICKS  # the arm stopped short (load sag / contact): done, not a timeout
        if (at_cmd and (err < self.reach_tol or settled)) or t > self.deadline:
            kind = ("reach" if err < self.reach_tol else "settled" if (settled and err <= BLOCKED_M) else "timeout")
            ev.append({"t": round(t, 3), "event": kind, "tag": self.cur.tag, "err_mm": round(err * 1e3, 1)})
            self._still = 0
            g = self.cur.grip
            if g in ("close", "open"):
                self.width = self.w_close if g == "close" else self.w_open
                self.wait_until = t + (CLOSE_WAIT_S if g == "close" else OPEN_WAIT_S)
                self.wait_action = g
                ev.append({"t": round(t, 3), "event": g, "tag": self.cur.tag,
                           "tcp": np.round(tcp, 4).tolist()})
            self.cur = None
        return self.cmd.copy(), self.width, ev


SmoothExec.rotate = MotionExec.rotate  # same orientation handling
