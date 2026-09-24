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
