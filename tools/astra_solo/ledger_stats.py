"""Token and cost breakdown of Astra-solo ledgers (no model calls): per call input / cached / output / reasoning
tokens, the KRW split between input and output, and the share of calls with cache hits.
usage: python tools/astra_solo/ledger_stats.py <ledger.jsonl> [...]"""
import json
import statistics
import sys

KRW = 1450.0
for p in sys.argv[1:]:
    rows = [json.loads(x) for x in open(p) if x.strip()]
    rows = [r for r in rows if r.get("usage")]
    inp = [int(r["usage"].get("input_tokens") or 0) for r in rows]
    cac = [int((r["usage"].get("input_tokens_details") or {}).get("cached_tokens") or 0) for r in rows]
    out = [int(r["usage"].get("output_tokens") or 0) for r in rows]
    rea = [int((r["usage"].get("output_tokens_details") or {}).get("reasoning_tokens") or 0) for r in rows]
    eff = {}
    for r in rows:
        eff.setdefault(r.get("effort"), 0)
        eff[r.get("effort")] += 1
    n = len(rows)
    in_krw = sum((i - c) * 10 + c * 1 for i, c in zip(inp, cac)) / 1e6 * KRW
    out_krw = sum(out) * 50 / 1e6 * KRW
    print(json.dumps({"ledger": p, "calls": n, "effort": eff, "input_med": statistics.median(inp),
                      "cached_med": statistics.median(cac), "calls_with_cache_hit": sum(c > 0 for c in cac),
                      "output_med": statistics.median(out), "reasoning_med": statistics.median(rea),
                      "visible_out_med": statistics.median([o - r for o, r in zip(out, rea)]),
                      "krw_input": round(in_krw, 1), "krw_output": round(out_krw, 1),
                      "krw_per_call": round((in_krw + out_krw) / n, 2)}))
