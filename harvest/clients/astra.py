"""Astra client over the OpenAI Responses API with streaming (first-token timing), no retries (canon §28 A6).
API errors (plan 2026-09-26 Task 21 D1, book 02 P108): a stream `error` event or `response.failed` sets rec.error to
the reported code (e.g. insufficient_quota, rate_limit_exceeded, server_error; "stream_error" / "response_failed"
without a code), never an empty answer; a non-200 status keeps rec.error = "http_<status>" and records the body's
code. error_code / error_message hold the API's code and message; api_error = the API itself reported the failure
(a client-side timeout or transport error is not one: the call may still have been billed). Final review I4: a
malformed `data:` line sets rec.error "bad_response" (the stream is read on, so a later usage is still recorded; the
`[DONE]` marker is skipped) and an httpx.StreamError (not an HTTPError) is recorded by its type like a transport
error -- neither raises into the caller."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field

import httpx

URL = "https://api.openai.com/v1/responses"


@dataclass
class AstraRecord:
    t_send: float = 0.0
    t_first_token: float = 0.0
    t_done: float = 0.0
    http_status: int | None = None
    usage: dict = field(default_factory=dict)
    output_text: str = ""
    model_field: str | None = None
    effort: str = ""
    image_sha256s: list = field(default_factory=list)
    error: str | None = None
    meta: dict = field(default_factory=dict)
    # F21 (prompt_health.md): a response.incomplete event / status "incomplete" (e.g. max_output_tokens truncation)
    incomplete: bool = False
    incomplete_reason: str | None = None
    # Task 21 D1: the API's own error report (stream error / response.failed / HTTP error body)
    error_code: str | None = None
    error_message: str | None = None
    api_error: bool = False


def _api_error(rec: AstraRecord, err, fallback: str, set_error: bool = True) -> None:
    err = err if isinstance(err, dict) else {}
    if rec.api_error and not err.get("code"):  # an error event's code is not overwritten by a code-less failure
        return
    rec.api_error = True
    rec.error_code = err.get("code") or None
    rec.error_message = err.get("message")
    if set_error:
        rec.error = rec.error_code or fallback


def _image_hashes(inp):
    out = []
    for msg in inp:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                url = part.get("image_url", "") if isinstance(part, dict) else ""
                if url.startswith("data:"):
                    out.append(hashlib.sha256(base64.b64decode(url.split(",", 1)[1])).hexdigest())
    return out


class AstraClient:
    def __init__(self, token: str, model: str, transport: httpx.BaseTransport | None = None, timeout_s=600.0):
        self.model = model
        self._c = httpx.Client(timeout=timeout_s, transport=transport,
                               headers={"Authorization": f"Bearer {token}"})

    def call(self, inp: list, effort: str, max_output_tokens: int, meta: dict) -> AstraRecord:
        rec = AstraRecord(effort=effort, meta=dict(meta), image_sha256s=_image_hashes(inp))
        body = {"model": self.model, "input": inp, "reasoning": {"effort": effort},
                "max_output_tokens": max_output_tokens, "stream": True}
        rec.t_send = time.monotonic()
        parts = []
        try:
            with self._c.stream("POST", URL, json=body) as resp:
                rec.http_status = resp.status_code
                if resp.status_code != 200:
                    resp.read()
                    rec.t_done = time.monotonic()
                    rec.error = f"http_{resp.status_code}"
                    try:
                        body = resp.json()
                    except ValueError:
                        body = {}
                    _api_error(rec, body.get("error") if isinstance(body, dict) else None, rec.error, set_error=False)
                    return rec
                for line in resp.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        continue
                    try:
                        ev = json.loads(data)
                    except ValueError:  # final review I4: a malformed line is a bad response, never an exception
                        rec.error = rec.error or "bad_response"
                        continue
                    if not isinstance(ev, dict):
                        rec.error = rec.error or "bad_response"
                        continue
                    if ev.get("type") == "response.output_text.delta":
                        if not parts:
                            rec.t_first_token = time.monotonic()
                        parts.append(ev.get("delta", ""))
                    elif ev.get("type") in ("response.completed", "response.incomplete"):
                        r = ev.get("response", {}) or {}
                        rec.model_field, rec.usage = r.get("model"), r.get("usage") or {}
                        if ev.get("type") == "response.incomplete" or r.get("status") == "incomplete":
                            rec.incomplete = True
                            rec.incomplete_reason = (r.get("incomplete_details") or {}).get("reason")
                            rec.error = f"incomplete:{rec.incomplete_reason}"
                    elif ev.get("type") == "error":
                        _api_error(rec, ev, "stream_error")
                    elif ev.get("type") == "response.failed":
                        r = ev.get("response", {}) or {}
                        rec.model_field, rec.usage = r.get("model"), r.get("usage") or {}
                        _api_error(rec, r.get("error"), "response_failed")
        except (httpx.HTTPError, httpx.StreamError) as e:  # StreamError is not an HTTPError (final review I4)
            rec.error = "timeout" if isinstance(e, httpx.TimeoutException) else type(e).__name__
            rec.error_message = str(e)[:500]
        rec.t_done = time.monotonic()
        rec.t_first_token = rec.t_first_token or rec.t_done
        rec.output_text = "".join(parts)
        return rec
