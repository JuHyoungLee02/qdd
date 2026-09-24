"""E-M8c cadence hooks (canon §45, pre-R7 fix 4): K1 subtask-boundary check, K3 Gemini-heartbeat faithful variant
(1 Hz opportunistic, waits for the previous turn, ack / run_instruction / reset), K4 event-only with a matched call
budget. Mock Astra only -- no paid API calls."""
import math

import numpy as np
import pytest

from harvest.runtime.astra_hb import (CADENCES, GEMINI_CHOICES, HeartbeatScheduler, MockAstra, ScriptedAstra,
                                      heartbeat_input, parse_decision, prompt_for)
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockSelector

from .fakeworld import FakeWorld


def test_k0_events_only():
    s = HeartbeatScheduler(N=5.0, mode="K0")
    assert s.next_kind(100.0) is None  # no periodic heartbeat, no boundary query
    s.boundary(3.0)
    assert s.next_kind(3.0) is None  # K0 has no T_sub
    s.advance(7.0)  # an event (T_fail, J5 escalation, critic alarm, ...)
    assert s.next_kind(7.0) == "hb"
    s.sent(7.0, "hb")
    s.responded(9.0)
    assert s.next_kind(50.0) is None


def test_k1_boundary_query_and_inflight_one():
    s = HeartbeatScheduler(N=5.0, mode="K1")
    assert s.next_kind(20.0) is None
    s.advance(1.0)
    s.sent(1.0, "hb")
    s.boundary(2.0)  # stage boundary while a call is in flight: queued, never overlapped
    assert s.next_kind(2.0) is None
    s.responded(3.5)
    assert s.next_kind(3.5) == "sub"
    s.sent(3.5, "sub")
    s.responded(6.0)
    assert s.next_kind(6.0) is None and s.n_by_kind == {"hb": 1, "sub": 1}


def test_k2_periodic_plus_boundary():
    s = HeartbeatScheduler(N=5.0, mode="K2")
    assert s.next_kind(4.9) is None and s.next_kind(5.0) == "hb"
    s.sent(5.0, "hb")
    s.responded(8.0)
    s.boundary(9.0)
    assert s.next_kind(9.0) == "sub"  # the boundary query goes first, then the period restarts after its answer
    s.sent(9.0, "sub")
    s.responded(10.0)
    assert s.next_kind(14.9) is None and s.next_kind(15.0) == "hb"


def test_k3_gemini_one_hz_waits_for_each_turn():
    s = HeartbeatScheduler(N=5.0, mode="K3")
    assert s.next_kind(0.0) == "hb"
    s.sent(0.0, "hb")
    s.responded(0.3)  # fast turn: wait for the 1 Hz slot
    assert s.next_kind(0.9) is None and s.next_kind(1.0) == "hb"
    s.sent(1.0, "hb")
    assert s.next_kind(2.0) is None  # the previous turn is not complete: never a second in flight
    s.responded(3.2)  # slow turn: send again as soon as it completes
    assert s.next_kind(3.2) == "hb"
    s.boundary(3.2)
    assert s.next_kind(3.2) == "hb"  # K3 has no separate boundary query


def test_k4_event_only_with_budget():
    s = HeartbeatScheduler(N=5.0, mode="K4", budget=2)
    assert s.next_kind(30.0) is None
    for t in (1.0, 5.0, 9.0):
        s.advance(t)
        k = s.next_kind(t)
        if k:
            s.sent(t, k)
            s.responded(t + 0.5)
    assert s.n_sent == 2 and s.next_kind(40.0) is None
    s.boundary(41.0)
    assert s.next_kind(41.0) is None  # budget spent


def test_prompts_and_parse_per_kind():
    assert CADENCES == ("K0", "K1", "K2", "K3", "K4")
    t_hb, allowed_hb, pid_hb = prompt_for("K2", "hb")
    t_sub, allowed_sub, pid_sub = prompt_for("K1", "sub")
    t_g, allowed_g, pid_g = prompt_for("K3", "hb")
    assert allowed_hb == allowed_sub == ("ack", "patch", "replace") and allowed_g == GEMINI_CHOICES
    assert len({pid_hb, pid_sub, pid_g}) == 3 and "run_instruction" in t_g and "next stage" in t_sub
    assert parse_decision('{"decision": "run_instruction", "note": "grasped"}', GEMINI_CHOICES) == \
        ("run_instruction", "grasped")
    assert parse_decision('{"decision": "reset"}', GEMINI_CHOICES)[0] == "reset"
    assert parse_decision('{"decision": "reset"}')[0] == "invalid"  # not an option of our heartbeat
    inp = heartbeat_input("s", None, template=t_g)
    assert "run_instruction" in inp[0]["content"][0]["text"]


def _run(mode, astra, seconds=40.0, budget=None):
    cfg = RuntimeConfig(backend="modular", clock="simlat", astra_mode="mock", hb_mode=mode, hb_budget=budget)
    rt = OursRuntime(cfg, MockSelector(latency_s=0.30), astra=astra)
    rt.reset()
    w = FakeWorld()
    for _ in range(int(seconds * 100)):
        a, _ = rt.act(w.obs())
        w.step(a)
    rt.close()
    return rt, w


def test_runtime_k1_asks_at_the_stage_boundary():
    rt, w = _run("K1", MockAstra(1.0))
    kinds = [a.get("kind") for a in rt.astra_log if "kind" in a]
    assert "sub" in kinds and "hb" not in kinds  # K1 = events + boundary, no periodic heartbeat
    assert any(e["event"] == "t_sub" for e in rt.events)
    assert np.all(np.abs(w.mug[:2] - w.tray[:2]) < [0.09, 0.07]) and not w.held


def test_runtime_k0_no_calls_without_events_and_k2_periodic():
    rt0, _ = _run("K0", MockAstra(1.0), seconds=20.0)
    assert len(rt0.astra_log) == 0
    rt2, _ = _run("K2", MockAstra(1.0), seconds=20.0)
    n = sum(1 for a in rt2.astra_log if a.get("kind") == "hb")
    assert 2 <= n <= 4  # every N = 5 s after the previous answer (1 s latency)


def test_runtime_k3_gemini_cadence_and_run_instruction_with_safety():
    """ScriptedAstra answers run_instruction once the mug is held and lifted in the image summary, reset after the
    release; the runtime applies them only when the code safety predicates hold."""
    rt, w = _run("K3", ScriptedAstra(latency_s=0.2), seconds=40.0)
    lat = [a for a in rt.astra_log if a.get("kind") == "hb"]
    assert len(lat) >= 25  # ~1 Hz (0.2 s turns), never overlapped
    sends = [a["t_send"] for a in lat]
    assert all(b - a >= 1.0 - 1e-6 for a, b in zip(sends, sends[1:]))
    acts = [e for e in rt.events if e["event"] == "astra_gemini"]
    assert any(e["decision"] == "run_instruction" and e["result"] == "applied" for e in acts)
    assert all(e["result"] in ("applied", "rejected", "noop") for e in acts)
    assert np.all(np.abs(w.mug[:2] - w.tray[:2]) < [0.09, 0.07]) and not w.held
    s = rt.summary()
    assert s["astra_decisions"]["run_instruction"] >= 1 and s["hb_mode"] == "K3"


def test_runtime_k4_respects_the_matched_budget():
    rt, _ = _run("K4", MockAstra(1.0), seconds=40.0, budget=1)
    assert len([a for a in rt.astra_log if "kind" in a]) <= 1
    assert rt.summary()["astra_budget"] == 1
