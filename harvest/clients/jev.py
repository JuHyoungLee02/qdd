"""Jev HTTP client: keep-alive, no retries, timing fields, raw JSON kept (E §1.1, §1.6)."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field

import httpx

from ..config import CFG


@dataclass
class CallRecord:
    call_id: str = ""
    experiment: str = ""
    condition: str = ""
    seed: int | None = None
    t_send: float = 0.0
    t_first_byte: float = 0.0
    t_done: float = 0.0
    http_status: int | None = None
    retry_n: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    model_ok: bool = True
    answers: dict = field(default_factory=dict)
    raw_request: dict = field(default_factory=dict)
    raw_response: dict | None = None
    error: str | None = None
    meta: dict = field(default_factory=dict)


class JevClient:
    def __init__(self, token: str, transport: httpx.BaseTransport | None = None):
        self._c = httpx.Client(timeout=CFG.timeout_s, transport=transport,
                               headers={"Authorization": f"Bearer {token}"})

    def call(self, req: dict, meta: dict) -> CallRecord:
        r = CallRecord(call_id=uuid.uuid4().hex, raw_request=req, meta=dict(meta),
                       experiment=meta.get("experiment", ""), condition=meta.get("condition", ""),
                       seed=meta.get("seed"))
        r.t_send = time.monotonic()
        try:
            with self._c.stream("POST", CFG.jev_url, json=req) as resp:
                chunks = resp.iter_bytes()
                first = next(chunks, b"")
                r.t_first_byte = time.monotonic()
                body = first + b"".join(chunks)
                r.t_done = time.monotonic()
                r.http_status = resp.status_code
        except httpx.TimeoutException:
            r.t_done = time.monotonic()
            r.t_first_byte = r.t_first_byte or r.t_done
            r.error = "timeout"
            return r
        except httpx.HTTPError as e:
            r.t_done = time.monotonic()
            r.t_first_byte = r.t_first_byte or r.t_done
            r.error = type(e).__name__
            return r
        if r.http_status != 200:
            r.error = f"http_{r.http_status}"
            return r
        data = json.loads(body)
        r.raw_response = data
        r.model = data.get("model")
        r.model_ok = r.model == CFG.jev_model
        usage = data.get("usage") or {}
        r.input_tokens, r.output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        r.answers = data.get("answers") or data.get("questions") or {}
        return r
