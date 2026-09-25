"""Paid-call cost ledger (canon §82 supplement: estimate before, track cumulative, stop before the limit).

Prices: OpenAI API pricing page (developers.openai.com/api/docs/pricing, read 2026-09-26): gpt-6-astra standard
input $10.00 / cached input $1.00 / output $50.00 per 1M tokens (reasoning tokens are billed as output tokens and are
included in usage.output_tokens). Local models cost 0. KRW_PER_USD is an assumption (conservative, stated in the
prereg), not a live rate.
"""
from __future__ import annotations

import json
import os
import time

PRICES_USD_PER_1M = {"gpt-6-astra": {"input": 10.0, "cached": 1.0, "output": 50.0}}
KRW_PER_USD = 1450.0
HARD_STOP_KRW = 15000.0  # probe re-scope (main session, 2026-09-25 ~17:55 UTC): cumulative hard stop 15,000 KRW


class BudgetStop(RuntimeError):
    pass


def cost_usd(model: str, usage: dict) -> float:
    pr = PRICES_USD_PER_1M.get(model)
    if not pr or not usage:
        return 0.0
    inp = int(usage.get("input_tokens", 0) or 0)
    cached = int(((usage.get("input_tokens_details") or {}).get("cached_tokens", 0)) or 0)
    out = int(usage.get("output_tokens", 0) or 0)
    return ((inp - cached) * pr["input"] + cached * pr["cached"] + out * pr["output"]) / 1e6


class Ledger:
    """Append-only cost log shared by every process of the probe (resumable: the total is re-read from the file)."""

    def __init__(self, path: str, hard_krw: float = HARD_STOP_KRW, krw_per_usd: float = KRW_PER_USD):
        import threading
        self.path, self.hard_krw, self.krw_per_usd = path, float(hard_krw), float(krw_per_usd)
        self.reserved_krw = 0.0  # maximum cost of this process's calls in flight
        self._lock = threading.Lock()

    @property
    def total_krw(self) -> float:
        """Sum of every row's cost in the shared file (several processes may append to it at once)."""
        if not os.path.exists(self.path):
            return 0.0
        return float(sum(float(json.loads(x)["cost_krw"]) for x in open(self.path) if x.strip()))

    def check(self, next_call_max_usd: float) -> None:
        """Raise BudgetStop when the next call could push the total (plus the maximum cost of calls already in
        flight) past the hard stop; otherwise reserve this call's maximum until add() releases it."""
        with self._lock:
            mx = next_call_max_usd * self.krw_per_usd
            if self.total_krw + self.reserved_krw + mx > self.hard_krw:
                raise BudgetStop(f"cumulative {self.total_krw:.0f} KRW + in flight {self.reserved_krw:.0f} + next "
                                 f"call max {mx:.0f} KRW > hard stop {self.hard_krw:.0f} KRW")
            self.reserved_krw += mx

    def add(self, rec: dict, reserved_usd: float = 0.0) -> float:
        usd = cost_usd(rec.get("model", ""), rec.get("usage") or {})
        krw = usd * self.krw_per_usd
        with self._lock:
            self.reserved_krw = max(0.0, self.reserved_krw - reserved_usd * self.krw_per_usd)
            row = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **rec, "cost_usd": round(usd, 6),
                   "cost_krw": round(krw, 4), "cum_krw": round(self.total_krw + krw, 2)}
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(row) + "\n")
        return usd
