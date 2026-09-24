"""Clock tracks for background model calls (canon §42, D23 §2): the same policy code, only delivery differs.

sync   : the world waits for the call; the answer is delivered at its send time (thinking is free).
simlat : a call sent at sim time t_s is delivered at t_s + its latency (measured wall latency, or a fixed synthetic
         latency for deterministic mocks). The world blocks only when the sim has run ahead of the wall clock since
         the send (then the answer could still arrive "in the past"), or when a fixed deadline is reached.
wall   : delivered as soon as done; `now` is wall-based (real robot, or a sim with RTF >= 1 that paces itself).
Each result is a dict carrying `latency_s`; the queue adds t_send / t_deliver.
"""
from __future__ import annotations

import time
from concurrent.futures import Future

MODES = ("sync", "simlat", "wall")


def _wait(fut: Future, timeout):
    try:
        return fut.result(timeout=timeout)
    except TimeoutError:
        return None


class DeliveryQueue:
    def __init__(self, mode: str, wall=time.monotonic):
        if mode not in MODES:
            raise ValueError(f"clock mode {mode!r}: one of {MODES}")
        self.mode, self.wall = mode, wall
        self._items: list[dict] = []
        self.blocked_s = 0.0

    def submit(self, t_send: float, future: Future, fixed_latency: float | None = None, meta=None) -> None:
        self._items.append({"t_send": float(t_send), "w_send": self.wall(), "fut": future,
                            "fixed": fixed_latency, "meta": meta})

    def inflight(self) -> int:
        return len(self._items)

    def _block(self, it, timeout, wait):
        w0 = self.wall()
        wait(it["fut"], timeout)
        self.blocked_s += self.wall() - w0

    def poll(self, now: float, wait=_wait) -> list[dict]:
        """Results due at sim/wall time `now`, ordered by delivery time."""
        out, keep = [], []
        for it in self._items:
            fut = it["fut"]
            if self.mode == "sync":
                if not fut.done():
                    self._block(it, None, wait)
                out.append(self._res(it, it["t_send"]))
                continue
            if self.mode == "wall":
                (out.append(self._res(it, now)) if fut.done() else keep.append(it))
                continue
            # simlat
            if not fut.done():
                if it["fixed"] is not None:
                    if now >= it["t_send"] + it["fixed"] - 1e-9:
                        self._block(it, None, wait)
                else:
                    ahead = (now - it["t_send"]) - (self.wall() - it["w_send"])
                    if ahead > 0:
                        self._block(it, ahead, wait)
            if fut.done():
                lat = it["fixed"] if it["fixed"] is not None else float(fut.result()["latency_s"])
                if now >= it["t_send"] + lat - 1e-9:
                    out.append(self._res(it, it["t_send"] + lat))
                    continue
            keep.append(it)
        self._items = keep
        return sorted(out, key=lambda r: r["t_deliver"])

    @staticmethod
    def _res(it, t_deliver):
        r = dict(it["fut"].result())
        r.update(t_send=it["t_send"], t_deliver=t_deliver, meta=it["meta"])
        return r
