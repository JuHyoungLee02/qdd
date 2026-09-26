"""Astra client at effort medium (request body, ledger, hard stop) and the pilot aggregation (success, KRW per success,
failure stages, per-call accuracy pairs)."""
import json

import httpx
import pytest

from harvest.astra_motion.cost import BudgetStop, Ledger
from harvest.astra_solo import analyze as AN
from harvest.astra_solo.models import SoloAstra


def _sse(text, usage):
    ev = [{"type": "response.output_text.delta", "delta": text},
          {"type": "response.completed", "response": {"model": "gpt-6-astra", "usage": usage, "status": "completed"}}]
    return "".join(f"data: {json.dumps(e)}\n\n" for e in ev)


def test_medium_effort_body_and_ledger(tmp_path):
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, text=_sse("{}", {"input_tokens": 2000, "output_tokens": 500}))
    led = Ledger(str(tmp_path / "l.jsonl"), hard_krw=5000.0)
    m = SoloAstra("tok", "medium", led, transport=httpx.MockTransport(handler))
    r = m.ask("hi", [("head camera", b"\x89PNG")], {"call": 0})
    assert seen["body"]["reasoning"] == {"effort": "medium"} and m.name == "astra-medium"
    assert seen["body"]["max_output_tokens"] == m.max_out and r.cost_usd > 0
    assert abs(led.total_krw - (2000 * 10 + 500 * 50) / 1e6 * 1450) < 1e-6


def test_quota_error_reaches_the_guard_unbilled(tmp_path):
    body = '{"error": {"message": "You exceeded your current quota", "code": "insufficient_quota"}}'
    led = Ledger(str(tmp_path / "l.jsonl"), hard_krw=5000.0)
    m = SoloAstra("tok", "low", led, transport=httpx.MockTransport(lambda r: httpx.Response(429, text=body)))
    r = m.ask("hi", [], {"call": 0})
    assert r.error == "http_429" and "insufficient_quota" in r.status and r.cost_usd == 0.0 and led.total_krw == 0.0


def test_hard_stop_before_the_call(tmp_path):
    led = Ledger(str(tmp_path / "l.jsonl"), hard_krw=10.0)
    m = SoloAstra("tok", "low", led, transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    with pytest.raises(BudgetStop):
        m.ask("hi", [], {"call": 0})


def R(success, stage, krw, n_calls, t=None, variant="standard"):
    return {"success": success, "fail_stage": stage, "cost_krw": krw, "n_calls": n_calls, "n_invalid": 0,
            "t_success": t, "variant": variant, "seed": 0, "grasp_lift": success, "calls": [], "wall_s": 10.0,
            "sim_t": 20.0, "end_reason": "success" if success else "stop"}


def test_summary_counts_success_cost_and_stages():
    s = AN.summarize([R(True, None, 600.0, 10, 30.0), R(False, "approach", 500.0, 12), R(False, "approach", 400.0, 9),
                      R(False, "place", 700.0, 14)])
    assert s["n"] == 4 and s["success"] == 1 and s["krw_total"] == 2200.0
    assert s["krw_per_success"] == 2200.0 and s["fail_stages"] == {"approach": 2, "place": 1}
    assert s["calls_per_episode"] == 11.25 and s["t_success_median"] == 30.0


def test_krw_per_success_without_success_is_none():
    assert AN.summarize([R(False, "approach", 500.0, 12)])["krw_per_success"] is None


def test_pairwise_effort_rule():
    pairs = [(30.0, 10.0)] * 9 + [(10.0, 30.0)] * 3  # (low err, medium err)
    assert AN.effort_rule(pairs)["verdict"] == "medium"
    assert AN.effort_rule([(10.0, 30.0)] * 8 + [(30.0, 10.0)] * 4)["verdict"] == "low"
    assert AN.effort_rule([(30.0, 25.0)] * 6 + [(25.0, 30.0)] * 6)["verdict"] == "undecided"
