"""OpenAI proxy of an open VLM in the Astra-solo arm (docs/stage3/prereg_open_vlm_solo.md): the same Responses-API
client as Astra with only the model id changed (gpt-5.2-2025-12-11), priced from the shared table; Astra's default
request stays byte-identical."""
import json

import httpx

from harvest.astra_motion.cost import Ledger, cost_usd
from harvest.astra_solo.models import SoloAstra
from harvest.astra_solo.run import make_model, paid_model

G52 = "gpt-5.2-2025-12-11"


def _sse(usage, model):
    ev = [{"type": "response.output_text.delta", "delta": "{}"},
          {"type": "response.completed", "response": {"model": model, "usage": usage, "status": "completed"}}]
    return "".join(f"data: {json.dumps(e)}\n\n" for e in ev)


def _run(tmp_path, **kw):
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, text=_sse({"input_tokens": 2000, "output_tokens": 500}, kw.get("model_id", "x")))
    led = Ledger(str(tmp_path / "l.jsonl"), hard_krw=3000.0)
    m = SoloAstra("tok", "low", led, transport=httpx.MockTransport(handler), **kw)
    r = m.ask("hi", [("head camera", b"\x89PNG")], {"call": 0})
    row = json.loads(open(tmp_path / "l.jsonl").read().splitlines()[0])
    return m, r, seen["body"], row, led


def test_price_table_has_gpt52():
    assert abs(cost_usd(G52, {"input_tokens": 1_000_000, "output_tokens": 1_000_000}) - (1.75 + 14.0)) < 1e-9


def test_price_table_has_gpt5_mini():  # prereg change 1: trainable-size proxy
    assert abs(cost_usd("gpt-5-mini-2025-08-07", {"input_tokens": 1_000_000, "output_tokens": 1_000_000}) - 2.25) < 1e-9


def test_proxy_changes_only_the_model_id(tmp_path):
    ma, _, ba, _, _ = _run(tmp_path / "a")
    mp, rp, bp, row, led = _run(tmp_path / "p", model_id=G52, name="gpt52")
    assert ba["model"] == "gpt-6-astra" and ma.name == "astra-low"
    assert bp["model"] == G52 and mp.name == "gpt52-low"
    assert {k: v for k, v in bp.items() if k != "model"} == {k: v for k, v in ba.items() if k != "model"}
    assert row["model"] == G52 and abs(rp.cost_usd - (2000 * 1.75 + 500 * 14.0) / 1e6) < 1e-12
    assert abs(led.total_krw - rp.cost_usd * 1450) < 1e-6
    assert abs(mp.max_call_usd - cost_usd(G52, {"input_tokens": 4000, "output_tokens": 6000})) < 1e-12


def test_runner_builds_proxy_and_treats_it_as_paid(tmp_path):
    tok = tmp_path / "t"
    tok.write_text("sk-abc\n")

    class A:
        api_model, token, ledger, cap_krw = G52, str(tok), str(tmp_path / "l.jsonl"), 3000.0
    m = make_model("proxy-low", A)
    assert isinstance(m, SoloAstra) and m.model_id == G52 and m.effort == "low" and m.name == "gpt-5.2-low"
    assert m.ledger.hard_krw == 3000.0
    assert paid_model("proxy-low") and paid_model("astra-low") and not paid_model("qwen8b")
