"""E-Couple / E-Astra-necessity (stream slot) evaluation pieces for harvest.eval.closed (spec §9, §15, §16; canon §82,
§84 supplement 2, 4, 5). Arms: off (no Astra at all when compared with a coupling arm = VLA alone), serial (one Astra
request in flight + two-layer M4), serial_pause (+ the optional phase pause, cost fallback). Paid runs need the run
day's price table, the pre-registered budget, a ledger path and a user approval reference -- the user's explicit
approval, obtained through the coordinator, of the purpose/call count/cost estimate (user-log 114, "돈드는건 내
허락맡고 하기"; replaces user-log 87's self-judged rule). Episodes cut by the 80 % budget stop are excluded from the judgment
and counted (plan ruling 10). couple_cell() also pools the per-episode chunk-level adherence (canon §84 supplement
4-5, controller ruling C4): CoupleDriver.summary()["adherence"] is already {"chunk_vs_offset": {n, follow_rate},
"chunk_vs_decision": {...}} per episode; the cell pools n x follow_rate across episodes (skipping None rates).
Plan Task 21: episodes whose stream was stopped by a fatal API error (summary couple.fatal, D1: insufficient_quota)
are excluded like budget-cut ones; the estimate adds the never-answered request of every episode (charged at the
reservation, max output tokens) as a separate line (B7).

  python -m harvest.eval.couple estimate --prices P.json --episodes 40 --episode-s 60 --latency-s 4 \
      --in-tokens 3500 --out-tokens 1000 [--phase-pause 8 --dense-frac 0.3] [--unanswered-per-episode 1]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

ARMS = ("off", "serial", "serial_pause")


def parse_arms(s: str) -> list:
    arms = [x for x in (s or "off").split(",") if x]
    if not arms or len(set(arms)) != len(arms) or any(x not in ARMS for x in arms):
        raise SystemExit(f"--couple {s!r}: distinct values from {ARMS}")
    return arms


def arm_config(arm: str, phase_pause_s: float = 3.0, min_interval_s: float = 0.0) -> dict:
    if arm == "off":
        return {"couple": "off"}
    cp = {"min_interval_s": float(min_interval_s)} if min_interval_s else {}
    if arm == "serial_pause":
        cp["phase_pause_s"] = float(phase_pause_s)
    return {"couple": "serial", "couple_params": cp}


def couple_label(label: str, arm: str, arms: list) -> str:
    return label if list(arms) == ["off"] else f"{label}|cp-{arm}"


def check_paid(a) -> None:
    miss = [k for k, ok in (("--couple-prices", bool(a.couple_prices)), ("--couple-budget-krw", a.couple_budget_krw > 0),
                            ("--couple-ledger", bool(a.couple_ledger)), ("--approval", bool(a.approval))) if not ok]
    if miss:
        raise SystemExit(f"paid Astra coupling run refused: {miss} missing (user-log 114: a user approval reference, "
                         f"the run day's prices, the pre-registered budget and a ledger)")


def stream_client(spec: dict):
    if spec.get("couple_upper") == "local":
        from ..couple.local_vlm import LocalVLMAstra
        return LocalVLMAstra(spec["couple_local_url"], spec["couple_local_model"]), "local"
    if spec["astra"] == "api":
        tok = "/data/.openai_token"
        if not os.path.exists(tok):
            raise SystemExit("--astra api but no /data/.openai_token")
        from ..clients.astra import AstraClient
        from ..runtime.astra_hb import MODEL
        return AstraClient(open(tok).read().strip(), MODEL, timeout_s=30.0), "api"
    from ..couple.mock import ScriptedCoupleAstra, answer
    # mock stream (pipeline smoke, no paid call): valid in both request modes (the request carries its mode)
    return ScriptedCoupleAstra(lambda req: answer("continue", views=(), diff="keep" if req.get("mode") == "F1" else None),
                               latency_s=3.0), "mock"


def is_budget_excluded(t: dict) -> bool:
    c = ((t.get("summary") or {}).get("couple")) or {}
    return bool(c.get("budget_excluded") or c.get("fatal"))


def fatal_code(rows: list):
    """The first fatal API error code (D1) in trial rows' couple summaries, else None."""
    for t in rows:
        f = (((t.get("summary") or {}).get("couple")) or {}).get("fatal")
        if f:
            return f
    return None


def _pool_adherence(cs: list, key: str) -> dict:
    """Pool one episode-level adherence field (n, follow_rate) across episodes: total n, and the n-weighted mean
    follow_rate (episodes without that rate, e.g. no active offset all episode, are skipped -- canon §84 supp 4-5)."""
    n_tot, w_tot = 0, 0.0
    for c in cs:
        a = ((c.get("adherence") or {}).get(key)) or {}
        n, rate = a.get("n") or 0, a.get("follow_rate")
        if rate is None or not n:
            continue
        n_tot += n
        w_tot += n * rate
    return {"n": n_tot, "follow_rate": round(w_tot / n_tot, 4) if n_tot else None}


def couple_cell(summaries: list):
    cs = [s.get("couple") for s in summaries if s.get("couple")]
    if not cs:
        return None

    def med(xs):
        xs = [x for x in xs if x is not None]
        return round(float(np.median(xs)), 4) if xs else None

    def tot(key):
        c = Counter()
        for x in cs:
            c.update(x.get(key) or {})
        return dict(c)
    return {"episodes": len(cs), "calls_per_episode": med([c["calls_sent"] for c in cs]),
            "latency_p50_s": med([c["latency_s"]["p50"] for c in cs]),
            "latency_p95_s": med([c["latency_s"]["p95"] for c in cs]),
            "answer_age_p50_s": med([c["answer_age_s"]["p50"] for c in cs]),
            "cost_krw_total": round(sum(c["cost_krw"] for c in cs), 3),
            "cost_krw_per_episode": med([c["cost_krw"] for c in cs]),
            "timeouts": sum(c["timeouts"] for c in cs), "schema_errors": sum(c["schema_errors"] for c in cs),
            "gates": tot("gates"), "layer": tot("layer"), "irrev": tot("irrev"), "events": tot("events"),
            "max_outstanding": max(c.get("max_outstanding", 1) for c in cs),
            "unanswered_n": sum(((c.get("unanswered") or {}).get("n") or 0) for c in cs),
            "unanswered_krw": round(sum(((c.get("unanswered") or {}).get("krw") or 0.0) for c in cs), 3),
            "adherence": {"chunk_vs_offset": _pool_adherence(cs, "chunk_vs_offset"),
                         "chunk_vs_decision": _pool_adherence(cs, "chunk_vs_decision")}}


def couple_diff(trials: list, n_boot: int) -> dict:
    """Paired success differences (same variant, seed, epoch) of each coupling arm against the off arm of the same
    base label; seed-cluster bootstrap (EVAL §4.2)."""
    from ..analysis.stats import cluster_mean_ci
    succ = {(t["condition"], t["variant"], t["seed"], t["epoch"]): int(bool(t["success"])) for t in trials}
    out = {}
    for c in sorted({t["condition"] for t in trials}):
        if "|cp-" not in c or c.endswith("|cp-off"):
            continue
        base = c.rsplit("|cp-", 1)[0] + "|cp-off"
        for v in sorted({t["variant"] for t in trials}):
            by = defaultdict(list)
            for (cc, vv, s, e), ok in succ.items():
                if cc == c and vv == v and (base, v, s, e) in succ:
                    by[s].append(ok - succ[(base, v, s, e)])
            if by:
                vals = [x for xs in by.values() for x in xs]
                lo, hi = cluster_mean_ci(by, n=n_boot, seed=0)
                out[f"{c} - {base}/{v}"] = {"mean": round(float(np.mean(vals)), 4), "ci": [round(lo, 4), round(hi, 4)],
                                            "n_pairs": len(vals), "n_seeds": len(by)}
    return out


def estimate(prices, episodes: int, episode_s: float, latency_s: float, in_tokens: int, out_tokens: int,
             phase_pause_s: float | None = None, dense_frac: float = 0.3, unanswered_per_episode: float = 1.0,
             max_output_tokens: int | None = None) -> dict:
    """unanswered_per_episode (B7): requests still in flight at each episode end, charged at the reservation
    (in_tokens + the stream's max_output_tokens, CoupleParams default) -- a separate line added in krw_total."""
    if max_output_tokens is None:
        from ..couple.params import CoupleParams
        max_output_tokens = CoupleParams().max_output_tokens
    if phase_pause_s is None:
        per_ep = episode_s / latency_s
    else:
        per_ep = dense_frac * episode_s / latency_s + (1 - dense_frac) * episode_s / max(latency_s, phase_pause_s)
    per_call = prices.krw({"input_tokens": in_tokens, "output_tokens": out_tokens})
    calls = episodes * per_ep
    u_calls, u_per = episodes * float(unanswered_per_episode), prices.krw_upper(in_tokens, max_output_tokens)
    un = {"per_episode": float(unanswered_per_episode), "calls": round(u_calls, 3), "krw_per_call": round(u_per, 3),
          "krw": round(u_calls * u_per, 1), "max_output_tokens": int(max_output_tokens)}
    return {"calls": round(calls, 3), "krw_per_call": round(per_call, 3), "krw": round(calls * per_call, 1),
            "unanswered": un, "krw_total": round(calls * per_call + u_calls * u_per, 1),
            "price_date": prices.date, "price_model": prices.model,
            "assumptions": {"episodes": episodes, "episode_s": episode_s, "latency_s": latency_s,
                            "in_tokens": in_tokens, "out_tokens": out_tokens, "phase_pause_s": phase_pause_s,
                            "dense_frac": dense_frac}}


def main(argv=None):
    from ..couple.cost import PriceTable
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("estimate")
    e.add_argument("--prices", required=True)
    e.add_argument("--episodes", type=int, required=True)
    e.add_argument("--episode-s", type=float, required=True)
    e.add_argument("--latency-s", type=float, required=True)
    e.add_argument("--in-tokens", type=int, required=True)
    e.add_argument("--out-tokens", type=int, required=True)
    e.add_argument("--phase-pause", type=float, default=None)
    e.add_argument("--dense-frac", type=float, default=0.3)
    e.add_argument("--unanswered-per-episode", type=float, default=1.0,
                   help="requests in flight at each episode end, charged at the reservation (plan Task 21 B7)")
    a = ap.parse_args(argv)
    r = estimate(PriceTable.load(a.prices), a.episodes, a.episode_s, a.latency_s, a.in_tokens, a.out_tokens,
                 a.phase_pause, a.dense_frac, a.unanswered_per_episode)
    print(json.dumps(r, indent=1))
    return r


if __name__ == "__main__":
    main(sys.argv[1:])
