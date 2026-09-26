"""Aggregation of Astra-solo episodes (pilot / dry run) and the paired effort rule (prereg §6).

summarize(results): success, grasp + lift, time to success (sim s of robot motion; median over successes), calls per
episode, invalid share, KRW total / per episode / per success, failure stages (probe Monitor stages) and a finer
approach breakdown (stagewise rule: no close / first close > 20 mm off in xy / closed above the object top).
effort_rule(pairs): pairs = [(low_xy_err_mm, medium_xy_err_mm)] for the same saved call inputs.
"""
from __future__ import annotations

import statistics
from collections import Counter

TIE_MM = 5.0
MIN_PAIRS = 8
BETTER_SHARE = 0.75
BETTER_MM = 10.0
WORSE_SHARE = 1.0 / 3.0


def approach_detail(r: dict) -> str | None:
    if r.get("fail_stage") != "approach":
        return None
    c = r.get("first_close")
    if not c:
        return "no_close"
    if c.get("above_top"):
        return "closed_above_top"
    return "close_xy_off"


def summarize(results: list) -> dict:
    n = len(results)
    succ = [r for r in results if r["success"]]
    krw = round(sum(float(r.get("cost_krw") or 0.0) for r in results), 2)
    calls = sum(r["n_calls"] for r in results)
    ts = [r["t_success"] for r in succ if r.get("t_success") is not None]
    return {"n": n, "success": len(succ), "grasp_lift": sum(bool(r.get("grasp_lift")) for r in results),
            "t_success_median": statistics.median(ts) if ts else None,
            "calls_per_episode": round(calls / n, 2) if n else None,
            "invalid_share": round(sum(r["n_invalid"] for r in results) / calls, 3) if calls else None,
            "krw_total": krw, "krw_per_episode": round(krw / n, 1) if n else None,
            "krw_per_success": round(krw / len(succ), 1) if succ else None,
            "fail_stages": dict(Counter(r["fail_stage"] for r in results if not r["success"] and r["fail_stage"])),
            "approach_detail": dict(Counter(d for d in map(approach_detail, results) if d)),
            "end_reasons": dict(Counter(r["end_reason"] for r in results)),
            "wall_s_median": statistics.median([r["wall_s"] for r in results]) if n else None}


def effort_rule(pairs: list) -> dict:
    """medium: medium is better (smaller error, beyond TIE_MM) in >= 75 % of the non-tied pairs and the median
    improvement over all pairs >= 10 mm; low: medium better in <= 1/3 of the non-tied pairs; else undecided.
    Fewer than MIN_PAIRS non-tied pairs -> undecided."""
    diffs = [lo - me for lo, me in pairs]
    nt = [d for d in diffs if abs(d) >= TIE_MM]
    better = sum(d > 0 for d in nt)
    med = statistics.median(diffs) if diffs else None
    out = {"n_pairs": len(pairs), "non_tied": len(nt), "medium_better": better, "median_improvement_mm": med}
    if len(nt) < MIN_PAIRS:
        return out | {"verdict": "undecided"}
    if better >= BETTER_SHARE * len(nt) and med is not None and med >= BETTER_MM:
        return out | {"verdict": "medium"}
    if better <= WORSE_SHARE * len(nt):
        return out | {"verdict": "low"}
    return out | {"verdict": "undecided"}
