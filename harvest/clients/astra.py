"""Astra client over the OpenAI Responses API with streaming (first-token timing), no retries (canon §28 A6)."""
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
                    return rec
                for line in resp.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    ev = json.loads(line[5:].strip())
                    if ev.get("type") == "response.output_text.delta":
                        if not parts:
                            rec.t_first_token = time.monotonic()
                        parts.append(ev.get("delta", ""))
                    elif ev.get("type") == "response.completed":
                        r = ev.get("response", {})
                        rec.model_field, rec.usage = r.get("model"), r.get("usage") or {}
        except httpx.HTTPError as e:
            rec.error = "timeout" if isinstance(e, httpx.TimeoutException) else type(e).__name__
        rec.t_done = time.monotonic()
        rec.t_first_token = rec.t_first_token or rec.t_done
        rec.output_text = "".join(parts)
        return rec
