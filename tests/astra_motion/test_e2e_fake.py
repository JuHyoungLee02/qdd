"""End to end on the kinematic fake world (no Isaac): the ground-truth model through synchronous S and the staggered
F0 / F1 schedules reaches full-task success; uncertain answers become continue; garbage output ends the episode as a
schema failure; the open-loop replay of logged staggered answers reproduces the live smooth run; the Astra client parses
the stream, logs cost and the hard stop fires before a call."""
import json

import httpx
import numpy as np
import pytest

from harvest.astra_motion import cost as C
from harvest.astra_motion import harness as H
from harvest.astra_motion import models as M
from harvest.astra_motion.truth import ASSESS, Rep, TruthModel

from .fakeworld import FakeWorld, GarbageModel


@pytest.mark.parametrize("task", ["mug_tray", "mug_marker", "bottle_tray"])
def test_sync_s_truth_succeeds(task, tmp_path):
    w = FakeWorld()
    res = H.run_episode(w, "S", TruthModel(w), seed=3, task=task, out_dir=str(tmp_path / "ep"))
    assert res["success"], (res["end_reason"], res["fail_stage"], res.get("s_history", [])[-3:])
    assert res["grasp_lift"] and res["fail_stage"] is None and res["first_close"]["err_mm"] < 6.0
    assert 5 <= res["n_calls"] <= H.N_SYNC and res["decisions"]["edit"] >= 5
    assert res["max_speed"] is not None and res["confidence"]["high"] == res["n_calls"]
    saved = json.load(open(tmp_path / "ep" / "result.json"))
    assert saved["success"]
    shots = sorted((tmp_path / "ep" / "calls").glob("c000_*/img*.png"))
    assert [p.name.split("_", 1)[1] for p in shots] == ["head_camera.png", "left_wrist_camera.png",
                                                        "right_wrist_camera.png"]


class Slow:
    """Wraps a model with a wall-clock delay (the staggered loop runs STAG_RT x real time)."""

    def __init__(self, m, delay_s):
        self.m, self.delay, self.name = m, delay_s, m.name

    def ask(self, text, images, meta):
        import time
        time.sleep(self.delay)
        return self.m.ask(text, images, meta)


@pytest.mark.parametrize("style", ["F0", "F1"])
def test_stagger_truth_succeeds_and_replays(style, monkeypatch):
    monkeypatch.setattr(H, "STAG_RT", 20.0)
    monkeypatch.setattr(H, "STAG_MAX_S", 200.0)
    monkeypatch.setattr(H, "STAG_MAX_CALLS", 120)
    w = FakeWorld()
    res = H.run_episode(w, f"S-stream-{style}", Slow(TruthModel(w), 0.15), seed=2, task="mug_tray")  # ~3 s latency
    sg = res["stream"]
    # F1 needs two serial answers per change (confirmation), so within the limit it only has to grasp and lift
    ok = res["success"] if style == "F0" else res["grasp_lift"]
    assert ok, (res["end_reason"], res["fail_stage"], [a.get("status") for a in sg["answers"]][:12])
    assert len(sg["answers"]) >= 5 and all(a["valid"] for a in sg["answers"])
    lat = sorted(a["arr_t"] - a["send_t"] for a in sg["answers"])
    assert lat[len(lat) // 2] > 1.5 and all(a["arr_t"] >= a["send_t"] for a in sg["answers"])  # serial, overlapping motion
    assert all(b["send_t"] >= a["arr_t"] - 1e-9 for a, b in zip(sg["answers"][:-1], sg["answers"][1:]))  # one in flight
    assert {"scale", "flip"} <= set(next(a for a in sg["answers"] if a.get("status") in ("applied", "keep")))
    if style == "F1":
        assert {"keep", "applied"} <= {a["status"] for a in sg["answers"]}
    live = (res["max_speed"], res["jerk_rms"])
    rs = H.replay(FakeWorld(), json.loads(json.dumps(res, default=H._jsonable)), "smooth")
    assert abs(rs["max_speed"] - live[0]) < 1e-6  # open-loop replay of the same answers = the live run
    ri = H.replay(FakeWorld(), json.loads(json.dumps(res, default=H._jsonable)), "immediate")
    assert ri["jerk_rms"] is not None and ri["max_speed"] >= rs["max_speed"] - 1e-9


class LowConfidence:
    """Every answer an edit (down 2 cm) but with confidence low -> treated as continue (no earlier motion -> hold)."""
    name = "lowconf"

    def ask(self, text, images, meta):
        a = dict(ASSESS, confidence="low")
        return Rep(json.dumps({"assessment": a, "decision": "edit", "edit": {"delta_position_cm": [0, 0, -2],
                                                                             "gripper": "keep"}}))


def test_uncertain_answers_become_continue():
    w = FakeWorld()
    res = H.run_episode(w, "S", LowConfidence(), seed=0, task="mug_tray", n_sync=4)
    assert res["n_uncertain_continue"] == 4 and res["confidence"]["low"] == 4
    assert np.allclose(res["tcp_path"][0][1:], res["tcp_path"][-1][1:])  # never moved


def test_garbage_output_is_schema_failure():
    w = FakeWorld()
    res = H.run_episode(w, "S", GarbageModel(), seed=0, task="mug_tray")
    assert res["end_reason"] == "schema" and not res["success"] and res["n_calls"] == 2 and res["n_invalid"] == 2
    assert res["fail_stage"] == "approach"


def test_references_run():
    w = FakeWorld()
    o = H.run_episode(w, "oracle", None, seed=1, task="mug_tray")
    assert o["success"] and o["n_calls"] == 0
    n = H.run_episode(w, "nomodel", None, seed=1, task="mug_tray")
    assert n["n_calls"] == 0 and n["first_close"] is not None  # closes at the object centroid (lower reference)


def test_video_frames(tmp_path):
    w = FakeWorld()
    res = H.run_episode(w, "S", TruthModel(w), seed=2, task="mug_tray", out_dir=str(tmp_path / "v"), video=True)
    assert res["success"] and len(list((tmp_path / "v" / "frames").glob("*.jpg"))) > 5


def test_same_command_and_opposite():
    e = lambda dp, g="keep": {"decision": "edit", "edit": {"delta_position_cm": dp, "delta_rotation_rad": [0, 0, 0],
                                                            "gripper": g}}
    assert H.same_command(e([3, 0, 0]), e([3, 1, 0])) and not H.same_command(e([3, 0, 0]), e([0, 3, 0]))
    assert not H.same_command(e([3, 0, 0]), e([3, 0, 0], "close"))
    assert H.opposite(e([3, 0, 0]), e([-3, 0.5, 0])) and not H.opposite(e([3, 0, 0]), e([0, 3, 0]))
    assert H.same_command(None, None) and not H.same_command(None, {"decision": "stop"})


# ---------------------------------------------------------------- Astra client (mock transport)
def _sse(events):
    return "".join(f"data: {json.dumps(e)}\n\n" for e in events).encode()


def test_astra_model_stream_usage_and_ledger(tmp_path):
    usage = {"input_tokens": 2000, "input_tokens_details": {"cached_tokens": 1024}, "output_tokens": 500,
             "output_tokens_details": {"reasoning_tokens": 300}}

    def handler(req):
        body = json.loads(req.content)
        assert body["model"] == "gpt-6-astra" and body["reasoning"]["effort"] == "low"
        assert body["prompt_cache_key"] == "astra_motion"
        assert any(p.get("type") == "input_image" for p in body["input"][0]["content"])
        return httpx.Response(200, content=_sse([{"type": "response.output_text.delta", "delta": '{"a"'},
                                                  {"type": "response.output_text.delta", "delta": ': 1}'},
                                                  {"type": "response.completed",
                                                   "response": {"model": "gpt-6-astra", "usage": usage}}]))
    L = C.Ledger(str(tmp_path / "cost.jsonl"))
    m = M.AstraModel("sk-test", "low", L, transport=httpx.MockTransport(handler))
    r = m.ask("hi", [("head camera", b"\x89PNG")], {"call": 0})
    assert r.text == '{"a": 1}' and r.error is None
    assert abs(r.cost_usd - (976 * 10 + 1024 * 1 + 500 * 50) / 1e6) < 1e-12
    assert abs(L.total_krw - r.cost_usd * C.KRW_PER_USD) < 1e-9 and L.reserved_krw == 0.0


def test_astra_cache_key_refused_falls_back(tmp_path):
    seen = []

    def handler(req):
        body = json.loads(req.content)
        seen.append("prompt_cache_key" in body)
        if "prompt_cache_key" in body:
            return httpx.Response(400, content=b'{"error": {"message": "Unknown parameter: prompt_cache_key"}}')
        return httpx.Response(200, content=_sse([{"type": "response.completed", "response": {
            "usage": {"input_tokens": 10, "output_tokens": 5}}}]))
    r = M.AstraModel("k", "low", C.Ledger(str(tmp_path / "c.jsonl")), transport=httpx.MockTransport(handler)).ask(
        "x", [], {})
    assert seen == [True, False] and r.error is None


def test_astra_incomplete_stream_keeps_usage(tmp_path):
    usage = {"input_tokens": 2000, "output_tokens": 6000}

    def handler(req):
        return httpx.Response(200, content=_sse([{"type": "response.incomplete", "response": {
            "status": "incomplete", "usage": usage, "incomplete_details": {"reason": "max_output_tokens"}}}]))
    L = C.Ledger(str(tmp_path / "cost.jsonl"))
    r = M.AstraModel("k", "low", L, transport=httpx.MockTransport(handler)).ask("x", [], {})
    assert r.error == "incomplete:max_output_tokens" and r.usage == usage and r.cost_usd > 0.3


def test_hard_stop_before_call(tmp_path):
    L = C.Ledger(str(tmp_path / "cost.jsonl"), hard_krw=100.0)
    called = []

    def handler(req):
        called.append(1)
        return httpx.Response(500)
    m = M.AstraModel("k", "high", L, transport=httpx.MockTransport(handler))
    w = FakeWorld()
    with pytest.raises(C.BudgetStop):
        H.run_episode(w, "S", m, seed=0, task="mug_tray")
    assert not called
