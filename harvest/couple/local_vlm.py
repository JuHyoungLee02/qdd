"""A local VLM in the Astra stream slot (E-Astra-necessity U-Q8 / U-Q4 / U-Q32, canon §82): OpenAI-compatible chat
on vLLM, the same call(inp, effort, max_output_tokens, meta) -> AstraRecord as clients.astra.AstraClient (effort is
recorded, not used). Same prompt bytes and images as Astra; no guided / JSON-schema decoding (canon §82 fairness:
Astra has none); temperature 0, seed 0."""
from __future__ import annotations

import time

import httpx

from ..clients.astra import AstraRecord, _image_hashes


def to_chat(inp: list) -> list:
    out = []
    for m in inp:
        parts = []
        for c in m["content"]:
            if c.get("type") == "input_text":
                parts.append({"type": "text", "text": c["text"]})
            elif c.get("type") == "input_image":
                parts.append({"type": "image_url", "image_url": {"url": c["image_url"]}})
        out.append({"role": m["role"], "content": parts})
    return out


class LocalVLMAstra:
    def __init__(self, base_url: str, model: str, timeout_s: float = 60.0, transport=None):
        self.base, self.served = base_url.rstrip("/"), model
        self.model = f"local:{model}"
        self._c = httpx.Client(timeout=timeout_s, transport=transport)

    def call(self, inp: list, effort: str, max_output_tokens: int, meta: dict) -> AstraRecord:
        rec = AstraRecord(effort=effort, meta={**meta, "effort_ignored": True}, image_sha256s=_image_hashes(inp))
        body = {"model": self.served, "messages": to_chat(inp), "max_tokens": int(max_output_tokens),
                "temperature": 0.0, "seed": 0}
        rec.t_send = time.monotonic()
        try:
            r = self._c.post(f"{self.base}/v1/chat/completions", json=body)
            rec.http_status = r.status_code
            if r.status_code != 200:
                rec.error = f"http_{r.status_code}"
            else:
                d = r.json()
                rec.output_text = d["choices"][0]["message"]["content"] or ""
                u = d.get("usage") or {}
                rec.usage = {"input_tokens": int(u.get("prompt_tokens", 0)),
                             "output_tokens": int(u.get("completion_tokens", 0))}
                rec.model_field = d.get("model")
        except httpx.HTTPError as e:
            rec.error = "timeout" if isinstance(e, httpx.TimeoutException) else type(e).__name__
        rec.t_done = time.monotonic()
        rec.t_first_token = rec.t_done
        return rec

    def close(self) -> None:
        self._c.close()
