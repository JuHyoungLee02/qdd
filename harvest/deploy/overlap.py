"""Overlapped upper-LLM scheduling (docs/stage3/prereg_deploy1.md; NOW.md §1-0f). Pure numpy, no Isaac.

The robot keeps moving while the upper thinks; the upper is asked again BEFORE the current move ends, so the next
command arrives about when it is needed. Pieces:
  schedule      when to ask next: S0 after arrival (baseline), S1 as soon as the previous answer arrived (continuous
                pipeline), S2(x) when the remaining time of the current move is x of the expected upper latency
                (x = 1: the answer lands at arrival; x < 1 later, x > 1 earlier = more overlap)
  AsyncUpper    simulated asynchrony in sim time: the request is taken from the scene at t_q (images + state snapshot),
                the model is called at once (the simulator is paused meanwhile), and the answer takes effect at
                t_q + latency (latency = the measured call time, or a sampled one); the sim keeps running in between
  stale check   when an answer lands: the destination is re-expressed on the object it points at (region tracking of
                the pointed object in the current head depth); if the object moved more than STALE_OBJ_M, or the
                command's premise changed (gripper state flipped since t_q), the answer is dropped and the upper is
                asked again at once
  stitch        RTC-style joining: a new command starts from the current commanded TCP and velocity (no stop) --
                the executor's continuity, checked here by the jump / speed-continuity metrics"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

STALE_OBJ_M = 0.02
SCHEDULES = ("S0", "S1", "S2")


def ask_now(schedule: str, x: float, busy: bool, pending: bool, t_left: float | None, lat_est: float) -> bool:
    """Whether to send the next upper request now.
    busy: the executor is still executing a command; pending: a request is already in flight;
    t_left: expected remaining time of the current move (None when unknown); lat_est: expected upper latency (s)."""
    if pending:
        return False
    if not busy:
        return True  # idle robot: always ask (every schedule)
    if schedule == "S0":
        return False
    if schedule == "S1":
        return True
    if schedule == "S2":
        return t_left is not None and t_left <= x * lat_est
    raise ValueError(schedule)


@dataclass
class Pending:
    t_q: float  # scene time of the request
    t_due: float  # when the answer takes effect
    answer: object  # the parsed reply
    snap: dict = field(default_factory=dict)  # state at t_q: grip closed?, holding?, object region points, ...


class AsyncUpper:
    """At most one request in flight. submit() calls the model now (sim paused) and holds the answer until t_due."""

    def __init__(self, call, latency_fn):
        self.call, self.latency_fn = call, latency_fn
        self.pending: Pending | None = None
        self.log = []

    def submit(self, t: float, request, snap: dict) -> None:
        ans, lat = self.call(request)
        lat = self.latency_fn(lat)
        self.pending = Pending(float(t), float(t) + float(lat), ans, snap)
        self.log.append({"t_q": round(t, 3), "lat_s": round(float(lat), 3)})

    def due(self, t: float) -> Pending | None:
        if self.pending is not None and t >= self.pending.t_due - 1e-9:
            p, self.pending = self.pending, None
            return p
        return None


def region_centroid(pts) -> np.ndarray | None:
    if pts is None or len(pts) == 0:
        return None
    return np.asarray(pts, float).mean(0)


def track_shift(pts_then, pts_now) -> np.ndarray:
    """Displacement of the pointed object between request and answer (centroid of its region points; zero if either
    view lost it)."""
    a, b = region_centroid(pts_then), region_centroid(pts_now)
    if a is None or b is None:
        return np.zeros(3)
    return b - a


def stale_check(snap: dict, now: dict, obj_m: float = STALE_OBJ_M):
    """-> (keep, reason, shift). Drop when the pointed object moved more than obj_m (the scene the upper saw is gone)
    or the gripper premise flipped (closed / holding at request vs now). Small moves are absorbed: the destination
    rides on the object (shift added by the caller)."""
    if bool(snap.get("holding")) != bool(now.get("holding")):
        return False, "holding_changed", np.zeros(3)
    if bool(snap.get("grip_closed")) != bool(now.get("grip_closed")):
        return False, "gripper_changed", np.zeros(3)
    sh = track_shift(snap.get("region"), now.get("region"))
    if float(np.linalg.norm(sh)) > obj_m:
        return False, "object_moved", sh
    return True, None, sh


def continuity(tcp_path, dt: float, v_stop: float = 0.01, min_stop_s: float = 0.3) -> dict:
    """Motion continuity of an episode's TCP path: stops (speed < v_stop for >= min_stop_s, excluding the first and
    last second), total stopped time, max speed jump between ticks (m/s)."""
    P = np.asarray(tcp_path, float)
    if len(P) < 3:
        return {"stops": 0, "stop_s": 0.0, "max_dv": 0.0}
    v = np.linalg.norm(np.diff(P, axis=0), axis=1) / dt
    k0, k1 = int(1.0 / dt), len(v) - int(1.0 / dt)
    slow = v < v_stop
    stops, run, tot = 0, 0, 0.0
    for i in range(max(k0, 0), max(k1, 0)):
        if slow[i]:
            run += 1
        else:
            if run * dt >= min_stop_s:
                stops += 1
                tot += run * dt
            run = 0
    if run * dt >= min_stop_s:
        stops += 1
        tot += run * dt
    return {"stops": stops, "stop_s": round(tot, 3), "max_dv": float(np.abs(np.diff(v)).max())}
