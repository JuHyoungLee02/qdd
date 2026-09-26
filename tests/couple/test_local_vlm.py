import json

import httpx

from harvest.couple.local_vlm import LocalVLMAstra, to_chat
from harvest.couple.params import CoupleParams
from harvest.couple.prompt import build_input

INP = build_input({"request_no": 1}, {"cam_head": b"\xff\xd8x"}, CoupleParams(), "task")


def test_responses_input_becomes_chat_messages():
    msgs = to_chat(INP)
    kinds = [c["type"] for c in msgs[0]["content"]]
    assert kinds == ["text", "text", "image_url"]
    assert msgs[0]["content"][2]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_call_maps_output_and_usage_without_guided_decoding():
    seen = {}

    def handler(req):
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"model": "qwen3-vl-8b", "choices": [{"message": {"content": '{"a": 1}'}}],
                                         "usage": {"prompt_tokens": 1500, "completion_tokens": 300}})
    c = LocalVLMAstra("http://vllm:8000", "qwen3-vl-8b", transport=httpx.MockTransport(handler))
    rec = c.call(INP, "low", 800, {"couple_no": 1})
    assert rec.output_text == '{"a": 1}' and rec.usage == {"input_tokens": 1500, "output_tokens": 300}
    assert rec.error is None and rec.meta["effort_ignored"] is True and c.model == "local:qwen3-vl-8b"
    assert seen["max_tokens"] == 800 and seen["temperature"] == 0.0 and "guided_json" not in seen


def test_http_error_and_timeout_are_recorded():
    c = LocalVLMAstra("http://vllm:8000", "m", transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    assert c.call(INP, "low", 10, {}).error == "http_503"

    def boom(req):
        raise httpx.ReadTimeout("slow", request=req)
    t = LocalVLMAstra("http://vllm:8000", "m", transport=httpx.MockTransport(boom))
    assert t.call(INP, "low", 10, {}).error == "timeout"
