import json

import httpx

from harvest.clients.astra import AstraClient

EVENTS = ('event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"{\\"a\\""}\n\n'
          'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":":1}"}\n\n'
          'event: response.completed\ndata: {"type":"response.completed","response":{"model":"m-1",'
          '"usage":{"input_tokens":10,"output_tokens":5}}}\n\n')


def test_stream_first_token_text_usage():
    seen = {}

    def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, content=EVENTS.encode(), headers={"content-type": "text/event-stream"})
    rec = AstraClient("k", "m-1", transport=httpx.MockTransport(handler)).call(
        [{"role": "user", "content": "hi"}], "low", 100, {"prompt_id": "p1"})
    assert rec.t_send <= rec.t_first_token <= rec.t_done
    assert rec.output_text == '{"a":1}' and rec.model_field == "m-1" and rec.usage["output_tokens"] == 5
    assert b'"effort": "low"' in seen["body"] or b'"effort":"low"' in seen["body"]


def test_http_error_recorded():
    rec = AstraClient("k", "m", transport=httpx.MockTransport(lambda r: httpx.Response(429, json={}))).call(
        [{"role": "user", "content": "hi"}], "high", 10, {})
    assert rec.error == "http_429" and rec.output_text == ""


def test_image_hashes_recorded():
    img = [{"role": "user", "content": [{"type": "input_image", "image_url": "data:image/png;base64,AAAA"}]}]
    t = httpx.MockTransport(lambda r: httpx.Response(200, content=EVENTS.encode()))
    rec = AstraClient("k", "m-1", transport=t).call(img, "low", 10, {})
    assert len(rec.image_sha256s) == 1 and len(rec.image_sha256s[0]) == 64


INCOMPLETE_EVENTS = (
    'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"{\\"a\\""}\n\n'
    'event: response.incomplete\ndata: {"type":"response.incomplete","response":{"model":"m-1","status":"incomplete",'
    '"usage":{"input_tokens":10,"output_tokens":600},'
    '"incomplete_details":{"reason":"max_output_tokens"}}}\n\n')


def test_incomplete_response_flagged_not_a_normal_answer():
    """F21 (prompt_health.md): response.incomplete (max_output_tokens truncation) must not be silently treated
    as a normal completed answer -- AstraRecord.incomplete/incomplete_reason record it and .error names it."""
    t = httpx.MockTransport(lambda r: httpx.Response(200, content=INCOMPLETE_EVENTS.encode(),
                                                     headers={"content-type": "text/event-stream"}))
    rec = AstraClient("k", "m-1", transport=t).call([{"role": "user", "content": "hi"}], "low", 600, {})
    assert rec.incomplete is True and rec.incomplete_reason == "max_output_tokens"
    assert rec.error == "incomplete:max_output_tokens"
    assert rec.output_text == '{"a"'  # the raw (truncated) text stays available, just not treated as a plain answer


def _sse(*events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


def _call(content, status=200):
    t = httpx.MockTransport(lambda r: httpx.Response(status, content=content,
                                                     headers={"content-type": "text/event-stream"}))
    return AstraClient("k", "m-1", transport=t).call([{"role": "user", "content": "hi"}], "low", 100, {})


def test_t21_stream_error_event_surfaces_the_code_not_an_empty_answer():
    """D1 / P108: credit exhaustion arrives as a stream `error` event; it must be an error, never an empty answer."""
    rec = _call(_sse({"type": "error", "code": "insufficient_quota", "param": None,
                      "message": "You exceeded your current quota"}))
    assert rec.error == "insufficient_quota" and rec.error_code == "insufficient_quota" and rec.api_error is True
    assert rec.error_message == "You exceeded your current quota" and rec.output_text == "" and rec.usage == {}


def test_t21_response_failed_surfaces_the_code():
    rec = _call(_sse({"type": "response.created", "response": {"model": "m-1"}},
                     {"type": "response.failed", "response": {"model": "m-1", "status": "failed", "usage": None,
                                                              "error": {"code": "server_error", "message": "boom"}}}))
    assert rec.error == "server_error" and rec.error_message == "boom" and rec.api_error is True
    assert rec.model_field == "m-1" and rec.usage == {}
    rec = _call(_sse({"type": "response.failed", "response": {"status": "failed"}}))
    assert rec.error == "response_failed" and rec.api_error is True
    rec = _call(_sse({"type": "error", "message": "?"}))
    assert rec.error == "stream_error"


def test_t21_http_error_body_code_recorded():
    rec = _call(json.dumps({"error": {"code": "insufficient_quota", "message": "quota", "type": "x"}}).encode(), 429)
    assert rec.error == "http_429" and rec.error_code == "insufficient_quota" and rec.error_message == "quota"
    assert rec.api_error is True


def test_t21_client_side_failure_is_not_an_api_error():
    def boom(request):
        raise httpx.ConnectError("down")
    rec = AstraClient("k", "m", transport=httpx.MockTransport(boom)).call([{"role": "user", "content": "hi"}],
                                                                          "low", 10, {})
    assert rec.error == "ConnectError" and rec.api_error is False and rec.error_code is None


def test_default_astra_record_is_not_incomplete():
    rec = AstraClient("k", "m-1", transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=EVENTS.encode()))).call(
        [{"role": "user", "content": "hi"}], "low", 100, {})
    assert rec.incomplete is False and rec.incomplete_reason is None and rec.error is None
