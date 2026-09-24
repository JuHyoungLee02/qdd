"""Astra H-cadence heartbeat (canon §45)."""
from harvest.runtime.astra_hb import (HB_PROMPT_ID, HeartbeatScheduler, MockAstra, heartbeat_input,
                                      parse_decision)


def test_scheduler_period_inflight_one_and_timeout():
    s = HeartbeatScheduler(N=5.0, timeout_s=15.0)
    assert not s.due(4.9) and s.due(5.0)
    s.sent(5.0)
    assert not s.due(30.0) or s.timed_out(30.0)  # in flight: only a timeout frees the slot
    assert not s.timed_out(19.9) and s.timed_out(20.1)
    s.responded(8.0)
    assert not s.due(12.9) and s.due(13.0)  # N seconds after the previous response arrived


def test_event_advances_next_heartbeat_and_pause():
    s = HeartbeatScheduler(N=5.0)
    s.advance(1.0)
    assert s.due(1.0)
    s.pause_until(10.0)
    assert not s.due(9.0) and s.due(10.0)


def test_parse_decision():
    assert parse_decision('{"decision": "ack", "note": "ok"}') == ("ack", "ok")
    assert parse_decision('```json\n{"decision":"replace","note":"x"}\n```')[0] == "replace"
    assert parse_decision("I think we should patch the plan")[0] == "patch"
    assert parse_decision("")[0] == "invalid"


def test_input_has_image_and_closed_choice():
    inp = heartbeat_input("stage S1 ...", b"\xff\xd8jpeg")
    parts = inp[-1]["content"]
    assert parts[0]["type"] == "input_text" and "ack" in parts[0]["text"] and "replace" in parts[0]["text"]
    assert parts[1]["type"] == "input_image" and parts[1]["image_url"].startswith("data:image/jpeg;base64,")
    assert len(HB_PROMPT_ID) == 12


def test_mock_astra_acks_with_fixed_latency():
    m = MockAstra(latency_s=3.0)
    rec = m.call([{"role": "user", "content": "x"}], "low", 400, {})
    assert parse_decision(rec.output_text)[0] == "ack" and m.synthetic_latency == 3.0 and rec.error is None
