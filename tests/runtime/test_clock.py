"""simlat / sync / wall delivery (canon §42, D23 §2)."""
from concurrent.futures import Future

import pytest

from harvest.runtime.clock import DeliveryQueue


class FakeWall:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def _done(value):
    f = Future()
    f.set_result(value)
    return f


def test_simlat_delivers_at_send_plus_measured_latency():
    w = FakeWall()
    q = DeliveryQueue("simlat", wall=w)
    q.submit(t_send=1.0, future=_done({"latency_s": 0.30, "x": 1}))
    assert q.poll(now=1.29) == []
    out = q.poll(now=1.30)
    assert [r["x"] for r in out] == [1] and out[0]["t_deliver"] == pytest.approx(1.30)
    assert q.inflight() == 0


def test_simlat_fixed_latency_blocks_until_done_at_deadline():
    w = FakeWall()
    q = DeliveryQueue("simlat", wall=w)
    f = Future()
    q.submit(t_send=0.0, future=f, fixed_latency=0.25)
    assert q.poll(now=0.1) == []
    waited = {}

    def block(fut, timeout):
        waited["timeout"] = timeout
        fut.set_result({"latency_s": 0.25, "x": 2})
        return fut.result()
    out = q.poll(now=0.25, wait=block)
    assert [r["x"] for r in out] == [2] and waited["timeout"] is None


def test_simlat_blocks_only_when_sim_runs_ahead_of_wall():
    w = FakeWall()
    q = DeliveryQueue("simlat", wall=w)
    f = Future()
    q.submit(t_send=0.0, future=f)
    w.t += 0.5  # 0.5 s of wall passed, sim only at 0.2 -> sim slower than wall, no blocking
    calls = []
    assert q.poll(now=0.2, wait=lambda fut, timeout: calls.append(timeout)) == [] and calls == []
    # sim at 0.9 s but only 0.5 s wall since send: the world must wait up to 0.4 s for the answer
    def block(fut, timeout):
        calls.append(timeout)
        w.t += 0.1
        fut.set_result({"latency_s": 0.6, "x": 3})
    out = q.poll(now=0.9, wait=block)
    assert calls[0] == pytest.approx(0.4)
    assert [r["x"] for r in out] == [3] and q.blocked_s == pytest.approx(0.1)


def test_sync_delivers_immediately_with_zero_sim_latency():
    q = DeliveryQueue("sync", wall=FakeWall())
    q.submit(t_send=2.0, future=_done({"latency_s": 0.4, "x": 4}))
    out = q.poll(now=2.0)
    assert out[0]["t_deliver"] == 2.0


def test_wall_delivers_when_done():
    q = DeliveryQueue("wall", wall=FakeWall())
    f = Future()
    q.submit(t_send=0.0, future=f)
    assert q.poll(now=5.0) == []
    f.set_result({"latency_s": 0.3, "x": 5})
    assert [r["x"] for r in q.poll(now=5.01)] == [5]


def test_delivery_order_by_deliver_time():
    q = DeliveryQueue("simlat", wall=FakeWall())
    q.submit(t_send=0.0, future=_done({"latency_s": 0.5, "x": "slow"}))
    q.submit(t_send=0.1, future=_done({"latency_s": 0.2, "x": "fast"}))
    assert [r["x"] for r in q.poll(now=1.0)] == ["fast", "slow"]


def test_bad_mode():
    with pytest.raises(ValueError):
        DeliveryQueue("realtime")
