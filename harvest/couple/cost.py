"""Paid-call cost ledger of the coupling stream (canon §82 supplement: ~100,000 KRW in total; spec §15: a budget cap
per experiment, written in its pre-registration, stop and report at 80 %). Prices come from the run day's price table
(a JSON file, never a constant in code). The ledger is an append-only JSONL file shared by the Isaac workers of one
experiment: every process re-reads new rows before deciding to send (spent grows only from the file), so parallel
workers see each other's charges; an in-flight reservation is local to its process (overshoot <= one call per
worker, inside the 20 % margin). Requests are reserved at the upper bound (no cache credit, max output tokens);
an answer replaces its reservation by the billed usage, a missing usage or a never-answered request is charged at
the reservation.
Plan 2026-09-26 Task 21 (book 02 P108): row kinds charge (billed usage), no_usage (the API reported an error and no
usage: it did not bill -> cost 0, reservation released), no_usage_reserved (no usage without an API error, e.g. a
client timeout: charged at the reservation), unanswered (never delivered by the episode end: charged at the
reservation, conservative -- the 80 % stop counts it; state() reports it apart from the answered spend, B7) and
fatal (cost 0: a fatal API error such as insufficient_quota; every ledger on the file stops sending, D1)."""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
from dataclasses import dataclass, fields

# canon §86 supplement 2 (docs/stage3/results/astra_motion.md §2 G1 v2): per-image input-token increment measured
# in the probe — 1 image ~588, 2 -> 738 (+150), 3 -> 892 (+154); TOK_WRIST is the average of those two deltas.
# TOK_HEAD is not separable from the text in the probe (no single-image call without the head cam), so it is kept
# at the probe's mean-input residual value.
TOK_HEAD, TOK_WRIST = 302, 152
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def estimate_input_tokens(text_tokens: int, cams) -> int:
    return int(text_tokens) + sum(TOK_HEAD if c == "cam_head" else TOK_WRIST for c in cams)


@dataclass(frozen=True)
class PriceTable:
    model: str
    date: str
    usd_per_mtok_input: float
    usd_per_mtok_cached_input: float
    usd_per_mtok_output: float
    krw_per_usd: float
    source: str

    @classmethod
    def load(cls, path: str) -> "PriceTable":
        d = json.load(open(path, encoding="utf-8"))
        miss = [f.name for f in fields(cls) if f.name not in d]
        if miss:
            raise ValueError(f"{path}: price table lacks {miss}")
        if not _DATE.match(str(d["date"])):
            raise ValueError(f"{path}: date {d['date']!r} is not YYYY-MM-DD")
        for k in ("usd_per_mtok_input", "usd_per_mtok_output", "krw_per_usd"):
            if not float(d[k]) > 0:
                raise ValueError(f"{path}: {k} must be > 0")
        if float(d["usd_per_mtok_cached_input"]) < 0:
            raise ValueError(f"{path}: usd_per_mtok_cached_input must be >= 0")
        return cls(model=str(d["model"]), date=str(d["date"]), usd_per_mtok_input=float(d["usd_per_mtok_input"]),
                   usd_per_mtok_cached_input=float(d["usd_per_mtok_cached_input"]),
                   usd_per_mtok_output=float(d["usd_per_mtok_output"]), krw_per_usd=float(d["krw_per_usd"]),
                   source=str(d["source"]))

    @classmethod
    def free(cls) -> "PriceTable":
        return cls("mock", "1970-01-01", 0.0, 0.0, 0.0, 1.0, "mock / local model: no charge")

    @property
    def is_free(self) -> bool:
        return self.usd_per_mtok_input == 0 and self.usd_per_mtok_output == 0 and self.usd_per_mtok_cached_input == 0

    def krw(self, usage: dict | None) -> float:
        u = usage or {}
        inp = int(u.get("input_tokens", 0) or 0)
        cached = int((u.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0)
        out = int(u.get("output_tokens", 0) or 0)
        usd = (max(inp - cached, 0) * self.usd_per_mtok_input + cached * self.usd_per_mtok_cached_input
               + out * self.usd_per_mtok_output) / 1e6
        return usd * self.krw_per_usd

    def krw_upper(self, est_in: int, max_out: int) -> float:
        return self.krw({"input_tokens": est_in, "output_tokens": max_out})


class CostLedger:
    def __init__(self, path: str | None, budget_krw: float, prices: PriceTable, stop_frac: float = 0.8,
                 run_id: str = ""):
        if not prices.is_free and not budget_krw > 0:
            raise ValueError("a priced ledger needs budget_krw > 0 (spec §15: the cap is pre-registered per experiment)")
        if not 0 < stop_frac <= 1:
            raise ValueError(f"stop_frac {stop_frac}: in (0, 1]")
        self.path, self.budget, self.prices = path, float(budget_krw), prices
        self.stop_frac, self.run_id = float(stop_frac), run_id
        self.spent, self._off, self.reserved = 0.0, 0, {}
        self.unanswered_n, self.unanswered_krw, self.fatal = 0, 0.0, None
        self.refresh()

    def _apply(self, row: dict) -> None:
        self.spent += float(row["cost_krw"])
        if row.get("kind") == "unanswered":
            self.unanswered_n += 1
            self.unanswered_krw += float(row["cost_krw"])
        elif row.get("kind") == "fatal" and self.fatal is None:
            self.fatal = row.get("code") or "fatal"

    @property
    def limit(self) -> float:
        return self.stop_frac * self.budget

    @property
    def stopped(self) -> bool:
        return self.budget > 0 and self.spent >= self.limit - 1e-9

    def refresh(self) -> None:
        if not self.path or not os.path.exists(self.path):
            return
        with open(self.path, "rb") as f:
            f.seek(self._off)
            data = f.read()
        end = data.rfind(b"\n")
        if end < 0:
            return
        for line in data[:end + 1].splitlines():
            if line.strip():
                self._apply(json.loads(line))
        self._off += end + 1

    def can_send(self, est_krw: float) -> bool:
        self.refresh()
        if self.budget <= 0:  # free prices only (__init__ refuses a priced ledger without a budget)
            return True
        return not self.stopped and self.spent + sum(self.reserved.values()) + est_krw <= self.limit + 1e-9

    def reserve(self, key: str, est_krw: float) -> None:
        self.reserved[key] = float(est_krw)

    def charge(self, key: str, usage: dict | None, meta: dict | None = None, api_error: bool = False) -> float:
        """api_error: the API itself reported the failure (AstraRecord.api_error); with no usage it did not bill."""
        est = self.reserved.pop(key, 0.0)
        if usage:
            kind, cost = "charge", self.prices.krw(usage)
        elif api_error:
            kind, cost = "no_usage", 0.0
        else:
            kind, cost = "no_usage_reserved", est
        self._append({**(meta or {}), "key": key, "kind": kind, "cost_krw": cost, "usage": usage or {}})
        return cost

    def finalize(self, prefix: str = "") -> tuple[int, float]:
        """Charge the never-answered reservations of `prefix` (kind unanswered); returns (n, krw)."""
        n, krw = 0, 0.0
        for k in [k for k in self.reserved if k.startswith(prefix)]:
            c = self.reserved.pop(k)
            self._append({"key": k, "kind": "unanswered", "cost_krw": c, "usage": {}})
            n, krw = n + 1, krw + c
        return n, krw

    def mark_fatal(self, code: str, message: str | None = None) -> None:
        """A fatal API error (D1: insufficient_quota): one cost-0 row; every ledger reading the file stops sending."""
        self.refresh()
        if self.fatal is None:
            self._append({"key": "fatal", "kind": "fatal", "code": code, "message": message, "cost_krw": 0.0,
                          "usage": {}})

    def _append(self, row: dict) -> None:
        row = {"t_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "run_id": self.run_id,
               "model": self.prices.model, "price_date": self.prices.date, "budget_krw": self.budget, **row}
        if not self.path:
            self._apply(row)
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        self.refresh()

    def state(self) -> dict:
        return {"spent_krw": round(self.spent, 3), "answered_krw": round(self.spent - self.unanswered_krw, 3),
                "unanswered_krw": round(self.unanswered_krw, 3), "unanswered_n": self.unanswered_n,
                "fatal": self.fatal, "reserved_krw": round(sum(self.reserved.values()), 3),
                "budget_krw": self.budget, "limit_krw": round(self.limit, 3), "stopped": self.stopped,
                "price_date": self.prices.date, "price_model": self.prices.model}
