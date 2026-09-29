"""Tables for docs/stage3/results/astra_solo_pilot.md from the pod outputs (no model calls).
usage: python tools/astra_solo/report.py --out <out root> --model astra-low [--reask <reask.jsonl>] [--ledger <l.jsonl>]
       [--json <summary.json>]
Prints markdown tables: per episode, summary per variant and overall, per-call approach target error, effort pairs."""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from harvest.astra_solo.analyze import approach_detail, effort_rule, summarize  # noqa: E402


def load(out, model):
    return [json.load(open(p)) for p in sorted(glob.glob(os.path.join(out, model, "*", "s*", "result.json")))]


def approach_err(r):
    v = [c["score"]["xy_err_mm"] for c in r["calls"] if c.get("score") and c["phase_truth"] == "approach"]
    return statistics.median(v) if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--reask")
    ap.add_argument("--ledger")
    ap.add_argument("--json")
    a = ap.parse_args()
    rs = load(a.out, a.model)
    order = {("standard", 0): 0, ("dr", 0): 1, ("standard", 1): 2, ("dr", 1): 3, ("standard", 2): 4, ("dr", 2): 5}
    rs.sort(key=lambda r: order.get((r["variant"], r["seed"]), 99))
    print("| 편 | 성공 | 파지+들기 | 실패 단계(세분) | 끝 이유 | 호출(자리) | 무효 | 성공까지 움직임 s | 벽시계 s | 원 | "
          "접근 목표 xy 오차 중앙 mm | 첫 닫기 xy mm | 잘림/막힘 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rs:
        fc = r.get("first_close") or {}
        st = r["fail_stage"] or "—"
        det = approach_detail(r)
        ae = approach_err(r)
        print(f"| {r['variant']} {r['seed']} | {int(r['success'])} | {int(r['grasp_lift'])} | {st}"
              f"{' (' + det + ')' if det else ''} | {r['end_reason']} | {r['n_calls']} ({r['n_sites']}) | "
              f"{r['n_invalid']} | {r['t_success'] if r['t_success'] is not None else '—'} | {r['wall_s']} | "
              f"{r['cost_krw']:.1f} | {ae if ae is not None else '—'} | {fc.get('err_xy_mm', '—')} | "
              f"{r['n_clipped']}/{r['n_blocked']} |")
    summ = {"all": summarize(rs)}
    for v in ("standard", "dr"):
        x = [r for r in rs if r["variant"] == v]
        if x:
            summ[v] = summarize(x)
    ae = [approach_err(r) for r in rs if approach_err(r) is not None]
    summ["approach_err_median_of_episode_medians_mm"] = statistics.median(ae) if ae else None
    lat = [x for r in rs for x in r["latency_s"]]
    summ["latency_p50_s"] = statistics.median(lat) if lat else None
    summ["latency_p95_s"] = sorted(lat)[int(0.95 * (len(lat) - 1))] if lat else None
    tin = sum(r["tokens_in"] for r in rs)
    tout = sum(r["tokens_out"] for r in rs)
    tre = sum(r["tokens_reasoning"] for r in rs)
    nc = sum(r["n_calls"] for r in rs)
    summ["tokens_per_call"] = {"in": round(tin / nc, 1) if nc else None, "out": round(tout / nc, 1) if nc else None,
                               "reasoning": round(tre / nc, 1) if nc else None}
    summ["krw_per_call"] = round(summ["all"]["krw_total"] / nc, 2) if nc else None
    print()
    print("| 묶음 | n | 성공 | 파지+들기 | 성공까지 움직임 중앙 s | 호출/편 | 무효율 | 원 합계 | 원/편 | 원/성공 | 실패 단계 | 접근 세분 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in ("all", "standard", "dr"):
        if k not in summ:
            continue
        s = summ[k]
        print(f"| {k} | {s['n']} | {s['success']} | {s['grasp_lift']} | {s['t_success_median'] or '—'} | "
              f"{s['calls_per_episode']} | {s['invalid_share']} | {s['krw_total']} | {s['krw_per_episode']} | "
              f"{s['krw_per_success'] or '—'} | {s['fail_stages']} | {s['approach_detail']} |")
    if a.reask and os.path.exists(a.reask):
        rows = [json.loads(x) for x in open(a.reask) if x.strip()]
        pairs = [(r["orig_xy_err_mm"], r["new_xy_err_mm"]) for r in rows if r.get("valid") and
                 r.get("new_xy_err_mm") is not None]
        rule = effort_rule(pairs)
        cost = sum(r["cost_usd"] for r in rows) * 1450.0
        summ["effort"] = {**rule, "n_rows": len(rows), "n_invalid": sum(not r["valid"] for r in rows),
                          "krw": round(cost, 1), "krw_per_call": round(cost / len(rows), 1) if rows else None,
                          "latency_p50_s": statistics.median([r["latency_s"] for r in rows]) if rows else None}
        print()
        print("| 짝 | 편 | 호출 | 단계 | low 모드 | low 오차 mm | medium 모드 | medium 오차 mm |")
        print("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(rows):
            print(f"| {i + 1} | {r['variant']} {r['seed']} | c{r['call']:03d} | {r['phase']} | {r['orig_mode']} | "
                  f"{r['orig_xy_err_mm']} | {r.get('new_mode', 'invalid')} | {r.get('new_xy_err_mm', '—')} |")
    if a.ledger and os.path.exists(a.ledger):
        led = [json.loads(x) for x in open(a.ledger) if x.strip()]
        summ["ledger"] = {"rows": len(led), "krw": round(sum(x["cost_krw"] for x in led), 2),
                          "first_utc": led[0]["utc"] if led else None, "last_utc": led[-1]["utc"] if led else None}
    print()
    print(json.dumps(summ, indent=1, ensure_ascii=False))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(summ, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
