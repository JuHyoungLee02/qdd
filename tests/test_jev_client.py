import httpx

from harvest.clients.jev import JevClient

REQ = {"model": "jev-1.13.0", "state": "s",
       "questions": {"ds1.dir_z": {"type": "choice", "instructions": "q", "criteria": {"up": "u", "down": "d"}}}}


def _transport(status=200, model="jev-1.13.0"):
    def handler(request):
        assert "authorization" in {k.lower() for k in request.headers}
        body = {"model": model, "usage": {"input_tokens": 1200, "output_tokens": 0},
                "answers": {"ds1.dir_z": {"choice": "up", "probabilities": {"up": 0.9, "down": 0.1}, "confidence": 0.9}}}
        return httpx.Response(status, json=body)
    return httpx.MockTransport(handler)


def test_parses_answer_and_times():
    r = JevClient("tok", transport=_transport()).call(REQ, {"experiment": "T"})
    assert r.http_status == 200 and r.answers["ds1.dir_z"]["choice"] == "up"
    assert r.t_send <= r.t_first_byte <= r.t_done and r.retry_n == 0 and r.model_ok
    assert r.input_tokens == 1200 and r.experiment == "T"


def test_model_mismatch_flags_session():
    r = JevClient("tok", transport=_transport(model="jev-1.14.0")).call(REQ, {})
    assert r.model_ok is False


def test_http_error_is_recorded_not_raised():
    r = JevClient("tok", transport=_transport(status=429)).call(REQ, {})
    assert r.http_status == 429 and r.error == "http_429"


def test_timeout_recorded():
    def boom(request):
        raise httpx.ReadTimeout("t", request=request)
    r = JevClient("tok", transport=httpx.MockTransport(boom)).call(REQ, {})
    assert r.http_status is None and r.error == "timeout" and r.t_done >= r.t_send
