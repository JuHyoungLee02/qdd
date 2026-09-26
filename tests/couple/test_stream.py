import json

import pytest

from harvest.couple.cost import CostLedger, PriceTable
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.couple.params import CoupleParams
from harvest.couple.prompt import build_input
from harvest.couple.stream import SerialStream

TEST = PriceTable("test", "2026-09-26", 2.0, 0.5, 8.0, 1400.0, "unit test")


def _s(**kw):
    return SerialStream(CoupleParams(**kw), CostLedger(None, 0.0, PriceTable.free()))


def test_one_request_in_flight_and_next_goes_on_answer():
    s = _s()
    assert s.next_send(0.0, False, 0.0) == (True, "send")
    no, ev = s.sent(0.0)
    assert (no, ev) == (1, [])
    assert s.next_send(1.0, True, 0.0) == (False, "inflight")
    s.delivered(1, 3.2, True, 3.2)
    assert s.next_send(3.2, False, 0.0) == (True, "send") and s.L_hat == pytest.approx(3.2)
    assert s.max_inflight == 1 and s.max_outstanding == 1


def test_max_inflight_counts_real_concurrent_calls():
    """Task 17 B2: sends minus deliveries / timeout drops (a dropped request's late answer no longer counts)."""
    s = _s(timeout_s=15.0)
    s.sent(0.0)
    s.timed_out(15.02)  # dropped: out of flight
    s.sent(15.02)
    assert s.is_late(1)
    s.delivered(2, 16.0, True, 1.0)
    assert s.max_inflight == 1 and s.max_outstanding == 2
    broken = _s()  # a caller that ignores next_send() and sends while one is in flight
    broken.sent(0.0)
    broken.sent(0.5)
    assert broken.max_inflight == 2
    broken.delivered(1, 1.0, True, 1.0)
    broken.delivered(2, 1.5, True, 1.0)
    broken.sent(2.0)
    assert broken.max_inflight == 2


def test_events_ride_on_the_next_request_only_once():
    s = _s()
    s.sent(0.0)
    s.flag("m7_critic_alarm", 0.5)
    s.flag("m7_critic_alarm", 0.6)
    s.flag("b_contradict", 0.7)
    s.delivered(1, 3.0, True, 3.0)
    assert s.sent(3.0) == (2, ["m7_critic_alarm", "b_contradict"])
    s.delivered(2, 6.0, True, 3.0)
    assert s.sent(6.0) == (3, [])


def test_timeout_frees_the_slot_late_answer_is_marked_and_failures_slow_down():
    s = _s(timeout_s=15.0)
    s.sent(0.0)
    assert s.timed_out(15.0) is None and s.timed_out(15.02) == 1
    assert s.next_send(15.02, False, 0.0) == (True, "send")
    s.sent(15.02)
    assert s.max_outstanding == 2 and s.is_late(1) and not s.is_late(2)
    for t in (30.1, 45.2):
        s.timed_out(t)
        s.sent(t)
    assert s.fail_streak == 3 and s.slowed(45.2)
    s.delivered(4, 47.0, True, 1.8)
    assert not s.slowed(47.0)
    s.request_slow(47.0)
    assert s.slowed(48.9) and not s.slowed(49.1)


def test_optional_phase_pause_and_min_interval():
    s = _s(phase_pause_s=3.0)
    s.sent(0.0)
    s.delivered(1, 1.0, True, 1.0)
    assert s.next_send(1.5, False, 0.0) == (False, "pause")
    assert s.next_send(1.5, True, 0.0) == (True, "send")
    s.flag("no_progress", 1.2)
    assert s.next_send(1.5, False, 0.0) == (True, "send")
    m = _s(min_interval_s=4.0)
    m.sent(0.0)
    m.delivered(1, 1.0, True, 1.0)
    assert m.next_send(3.9, False, 0.0) == (False, "min_interval") and m.next_send(4.0, False, 0.0)[0]


def test_budget_blocks_the_send():
    s = SerialStream(CoupleParams(), CostLedger(None, 1.0, TEST))
    assert s.next_send(0.0, False, 0.9) == (False, "budget")


def test_scripted_astra_answers_in_order_and_sees_the_request():
    ast = ScriptedCoupleAstra([answer("continue"), answer("edit", execution="failed", dp=(0, 0, 0.01))],
                              latency_s=2.0, usage={"input_tokens": 3000, "output_tokens": 900})
    p = CoupleParams(request_mode="F0")
    for n in (1, 2, 3):
        rec = ast.call(build_input({"request_no": n}, {}, p, "task"), "low", 1200, {"couple_no": n})
        assert rec.usage["output_tokens"] == 900 and rec.effort == "low"
    assert [c["req"]["request_no"] for c in ast.calls] == [1, 2, 3]
    assert json.loads(rec.output_text)["command"] == "edit" and ast.synthetic_latency == 2.0
    dyn = ScriptedCoupleAstra(lambda req: answer("stop" if req["request_no"] > 1 else "continue"))
    assert json.loads(dyn.call(build_input({"request_no": 2}, {}, p, "t"), "low", 10, {}).output_text)["command"] == "stop"
