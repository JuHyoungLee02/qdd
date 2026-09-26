"""Model clients for the probe: Astra (OpenAI Responses API, streaming, cost ledger with hard stop) and a local VLM
(vLLM OpenAI chat server). Both take the same text + labelled images."""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field

import httpx

from .cost import Ledger, cost_usd

URL = "https://api.openai.com/v1/responses"
ASTRA = "gpt-6-astra"
MAX_OUT = {"low": 6000, "high": 20000}
MAX_IN_TOKENS = 4000  # bound used for the pre-call budget check (measured prompts are ~2-3k)


@dataclass
class Reply:
    text: str = ""
    usage: dict = field(default_factory=dict)
    latency_s: float = 0.0
    first_token_s: float = 0.0
    error: str | None = None
    model_field: str | None = None
    cost_usd: float = 0.0
    status: str | None = None


def _data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode()


class AstraModel:
    """gpt-6-astra at one reasoning effort. Every call: budget check (hard stop) before, ledger row after. A call whose
    usage never arrived (network error / cut stream) is charged its maximum cost (conservative).
    model_id = the Responses-API model (default gpt-6-astra; a subclass may set another id priced in cost.py)."""

    model_id = ASTRA

    def __init__(self, token: str, effort: str, ledger: Ledger, transport: httpx.BaseTransport | None = None,
                 timeout_s: float = 900.0, cache_key: str | None = "astra_motion", extra: dict | None = None):
        self.effort, self.ledger = effort, ledger
        self.extra = dict(extra or {})  # determinism settings the API accepted (api_params_probe)
        self.name = f"astra-{effort}"
        self.max_out = MAX_OUT[effort]
        self.max_call_usd = cost_usd(self.model_id, {"input_tokens": MAX_IN_TOKENS, "output_tokens": self.max_out})
        self.cache_key = cache_key  # Responses API prompt_cache_key (routing hint for the shared prefix)
        self._c = httpx.Client(timeout=timeout_s, transport=transport, headers={"Authorization": f"Bearer {token}"})

    def ask(self, text: str, images: list, meta: dict) -> Reply:
        self.ledger.check(self.max_call_usd)
        try:
            r = self._ask(text, images, meta)
            if r.error == "http_400" and self.cache_key and "prompt_cache_key" in (r.status or ""):
                self.cache_key = None  # the API refused the parameter: resend once without it (a 400 is not billed)
                r = self._ask(text, images, meta)
        except BaseException:
            self.ledger.add({"model": self.model_id, "effort": self.effort, "usage": {}, "meta": meta,
                             "error": "exception"}, reserved_usd=self.max_call_usd)
            raise
        usage, charged_max = r.usage, False
        if not usage and r.error and not r.error.startswith("http_4"):
            usage, charged_max = {"input_tokens": MAX_IN_TOKENS, "output_tokens": self.max_out}, True
        r.cost_usd = self.ledger.add({"model": self.model_id, "effort": self.effort, "usage": usage, "meta": meta,
                                      "latency_s": round(r.latency_s, 3), "first_token_s": round(r.first_token_s, 3),
                                      "error": r.error, "charged_max": charged_max, "model_field": r.model_field,
                                      "cache_key": self.cache_key}, reserved_usd=self.max_call_usd)
        return r

    def _ask(self, text: str, images: list, meta: dict) -> Reply:
        content = [{"type": "input_text", "text": text}]
        for i, (label, png) in enumerate(images):
            content.append({"type": "input_text", "text": f"Image {i + 1}: {label}"})
            content.append({"type": "input_image", "image_url": _data_url(png), "detail": "high"})
        body = {"model": self.model_id, "input": [{"role": "user", "content": content}],
                "reasoning": {"effort": self.effort}, "max_output_tokens": self.max_out, "stream": True}
        if self.cache_key:
            body["prompt_cache_key"] = self.cache_key
        body.update(self.extra)
        r = Reply()
        t0 = time.monotonic()
        parts = []
        try:
            with self._c.stream("POST", URL, json=body) as resp:
                if resp.status_code != 200:
                    raw = resp.read()
                    r.error = f"http_{resp.status_code}"
                    r.status = raw.decode("utf-8", "replace")[:500]
                else:
                    for line in resp.iter_lines():
                        if not line.startswith("data:"):
                            continue
                        ev = json.loads(line[5:].strip())
                        typ = ev.get("type", "")
                        if typ == "response.output_text.delta":
                            if not parts:
                                r.first_token_s = time.monotonic() - t0
                            parts.append(ev.get("delta", ""))
                        elif typ in ("response.completed", "response.incomplete", "response.failed"):
                            rr = ev.get("response", {}) or {}
                            r.model_field, r.usage, r.status = rr.get("model"), rr.get("usage") or {}, rr.get("status")
                            if typ != "response.completed":
                                r.error = f"{typ.split('.')[-1]}:{(rr.get('incomplete_details') or {}).get('reason')}"
        except httpx.HTTPError as e:
            r.error = "timeout" if isinstance(e, httpx.TimeoutException) else type(e).__name__
        r.latency_s = time.monotonic() - t0
        r.first_token_s = r.first_token_s or r.latency_s
        r.text = "".join(parts)
        return r


def api_params_probe(token: str, ledger: Ledger, transport: httpx.BaseTransport | None = None) -> dict:
    """Which determinism settings the Responses API accepts for gpt-6-astra (effort low, a 3-word prompt,
    max_output_tokens 16 each): temperature 0, top_p 1, seed 0. A refused parameter returns HTTP 400 (not billed);
    accepted calls are billed and logged in the ledger."""
    c = httpx.Client(timeout=120.0, transport=transport, headers={"Authorization": f"Bearer {token}"})
    out = {}
    for name, extra in (("temperature", {"temperature": 0.0}), ("top_p", {"top_p": 1.0}), ("seed", {"seed": 0})):
        body = {"model": ASTRA, "input": "Reply with OK.", "reasoning": {"effort": "low"}, "max_output_tokens": 16,
                **extra}
        ledger.check(0.01)
        r = c.post(URL, json=body)
        usage = {}
        if r.status_code == 200:
            usage = r.json().get("usage") or {}
        usd = ledger.add({"model": ASTRA, "effort": "low", "usage": usage, "meta": {"kind": "api_params", "param":
                                                                                    name}}, reserved_usd=0.01)
        msg = "" if r.status_code == 200 else r.text[:300]
        out[name] = {"http": r.status_code, "accepted": r.status_code == 200, "message": msg, "cost_usd": usd}
    return out


class LocalVLM:
    """A local VLM behind a vLLM OpenAI-compatible chat server; greedy decoding. Cost 0."""

    def __init__(self, base_url: str, served_name: str, label: str, max_tokens: int = 2000, timeout_s: float = 300.0,
                 transport: httpx.BaseTransport | None = None):
        self.url, self.served, self.name, self.max_tokens = base_url.rstrip("/"), served_name, label, max_tokens
        self._c = httpx.Client(timeout=timeout_s, transport=transport)

    def ask(self, text: str, images: list, meta: dict) -> Reply:
        content = [{"type": "text", "text": text}]
        for i, (label, png) in enumerate(images):
            content.append({"type": "text", "text": f"Image {i + 1}: {label}"})
            content.append({"type": "image_url", "image_url": {"url": _data_url(png)}})
        body = {"model": self.served, "messages": [{"role": "user", "content": content}], "temperature": 0.0,
                "max_tokens": self.max_tokens, "seed": 0}
        r = Reply()
        t0 = time.monotonic()
        try:
            resp = self._c.post(f"{self.url}/v1/chat/completions", json=body)
            if resp.status_code != 200:
                r.error = f"http_{resp.status_code}:{resp.text[:200]}"
            else:
                d = resp.json()
                r.text = d["choices"][0]["message"]["content"] or ""
                u = d.get("usage") or {}
                r.usage = {"input_tokens": u.get("prompt_tokens"), "output_tokens": u.get("completion_tokens")}
                r.model_field = d.get("model")
        except httpx.HTTPError as e:
            r.error = "timeout" if isinstance(e, httpx.TimeoutException) else type(e).__name__
        r.latency_s = r.first_token_s = time.monotonic() - t0
        return r
