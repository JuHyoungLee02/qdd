"""E-ACC Astra client (prereg change 3): the production harvest.clients.astra.AstraClient request (same body, same
streaming, no retries) but the stream's `error` and `response.failed` events are reported in rec.error as
'failed:<code>' (the production client drops them -- E-ACC result D1). The runner stops the whole run on
'failed:insufficient_quota' / credit exhaustion and after 3 empty answers without usage in a row."""
from __future__ import annotations

import json
import time

from harvest.clients.astra import URL, AstraClient, AstraRecord, _image_hashes

FATAL_CODES = ("insufficient_quota", "credit_balance_exhausted", "billing_hard_limit_reached")


class EaccAstraClient(AstraClient):
    def call(self, inp: list, effort: str, max_output_tokens: int, meta: dict) -> AstraRecord:
        rec = AstraRecord(effort=effort, meta=dict(meta), image_sha256s=_image_hashes(inp))
        body = {"model": self.model, "input": inp, "reasoning": {"effort": effort},
                "max_output_tokens": max_output_tokens, "stream": True}
        if meta.get("cache_key"):  # prereg change 4: request field only, the model input is unchanged
            body["prompt_cache_key"] = meta["cache_key"]
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
                    t = ev.get("type")
                    if t == "response.output_text.delta":
                        if not parts:
                            rec.t_first_token = time.monotonic()
                        parts.append(ev.get("delta", ""))
                    elif t in ("error", "response.failed"):
                        err = ev.get("error") or (ev.get("response") or {}).get("error") or {}
                        rec.error = rec.error or f"failed:{err.get('code') or err.get('type') or 'unknown'}"
                    elif t in ("response.completed", "response.incomplete"):
                        r = ev.get("response", {})
                        rec.model_field, rec.usage = r.get("model"), r.get("usage") or {}
                        if t == "response.incomplete" or r.get("status") == "incomplete":
                            rec.error = f"incomplete:{(r.get('incomplete_details') or {}).get('reason')}"
        except Exception as e:  # noqa: BLE001 - network errors are recorded, never retried
            rec.error = "timeout" if "Timeout" in type(e).__name__ else type(e).__name__
        rec.t_done = time.monotonic()
        rec.t_first_token = rec.t_first_token or rec.t_done
        rec.output_text = "".join(parts)
        return rec


def is_fatal(rec) -> bool:
    return bool(rec.error) and any(c in rec.error for c in FATAL_CODES)


def is_empty(rec) -> bool:
    return not (rec.output_text or "").strip() and not (rec.usage or {}).get("output_tokens")
