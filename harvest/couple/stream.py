"""Serial Astra stream (canon §84 supplement 2, spec §16): ONE request in flight; when its answer (or the timeout)
arrives the next request goes out with the latest observation, so the interval = the latency L. Events raised while a
request is out do not cancel it: they are attached to the next request (flag). Options: min_interval_s (E-Astra-
necessity pacing of a fast local model), phase_pause_s (cost fallback: outside contact windows and more than
event_window_s after an event, wait until last send + phase_pause_s). A timed-out request frees the slot; if its
answer still arrives it is 'late' (never applied, still charged). fail_slow_after failed calls in a row (timeout,
API error, schema error) slow the robot down (spec §7) until a valid answer. max_inflight = the true maximum of
concurrent requests (sends minus deliveries and timeout drops; 1 in a correct serial run); max_outstanding also
counts dropped requests whose late answer has not come back."""
from __future__ import annotations

import math
import statistics
from collections import deque


class SerialStream:
    def __init__(self, p, ledger):
        self.p, self.ledger = p, ledger
        self.inflight = None  # (request no, t_send)
        self.n_sent, self.fail_streak = 0, 0
        self.dropped, self.outstanding = set(), set()
        self.live = set()  # requests really in flight: + on send, - on delivery or timeout drop (Task 17 B2)
        self.last_send = None
        self.pending_events = []
        self.last_event_t = -math.inf
        self.slow_until = -math.inf
        self.lat = deque(maxlen=20)
        self.max_inflight, self.max_outstanding = 0, 0
        self.counts = {"sent": 0, "answered": 0, "failed": 0, "timeouts": 0, "late": 0}

    def flag(self, name: str, now: float) -> None:
        if name not in self.pending_events:
            self.pending_events.append(name)
        self.last_event_t = now

    def next_send(self, now: float, contact_window: bool, est_krw: float) -> tuple[bool, str]:
        if self.inflight is not None:
            return False, "inflight"
        if self.last_send is not None and now < self.last_send + self.p.min_interval_s - 1e-9:
            return False, "min_interval"
        pp = self.p.phase_pause_s
        if (pp is not None and self.last_send is not None and not contact_window
                and now - self.last_event_t > self.p.event_window_s + 1e-9 and now < self.last_send + pp - 1e-9):
            return False, "pause"
        if not self.ledger.can_send(est_krw):
            return False, "budget"
        return True, "send"

    def sent(self, now: float) -> tuple[int, list]:
        self.n_sent += 1
        no = self.n_sent
        self.inflight, self.last_send = (no, now), now
        self.outstanding.add(no)
        self.live.add(no)
        self.max_inflight = max(self.max_inflight, len(self.live))
        self.max_outstanding = max(self.max_outstanding, len(self.outstanding))
        self.counts["sent"] += 1
        ev, self.pending_events = self.pending_events, []
        return no, ev

    def timed_out(self, now: float):
        if self.inflight is None or now - self.inflight[1] <= self.p.timeout_s + 1e-9:
            return None
        no = self.inflight[0]
        self.inflight = None
        self.live.discard(no)  # a late answer of a dropped request no longer counts as in flight
        self.dropped.add(no)
        self.fail_streak += 1
        self.counts["timeouts"] += 1
        return no

    def is_late(self, no: int) -> bool:
        if no not in self.dropped:
            return False
        self.outstanding.discard(no)
        self.counts["late"] += 1
        return True

    def delivered(self, no: int, now: float, ok: bool, latency: float) -> None:
        self.outstanding.discard(no)
        self.live.discard(no)
        if self.inflight is not None and self.inflight[0] == no:
            self.inflight = None
        if ok:
            self.fail_streak = 0
            self.counts["answered"] += 1
            self.lat.append(float(latency))
        else:
            self.fail_streak += 1
            self.counts["failed"] += 1

    @property
    def L_hat(self) -> float:
        return float(statistics.median(self.lat)) if self.lat else float(self.p.latency_init_s)

    def slowed(self, now: float) -> bool:
        return self.fail_streak >= self.p.fail_slow_after or now < self.slow_until - 1e-9

    def request_slow(self, now: float) -> None:
        self.slow_until = max(self.slow_until, now + self.p.slow_down_s)
