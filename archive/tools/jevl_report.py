"""Summarize Jev-L pre-test (1) rows (jevl_bench.py output) against the pre-registered L1-L3 rules."""
import json
import math
import sys
from collections import Counter, defaultdict

from harvest.analysis.latency import censored_quantile

rows = [json.loads(x) for x in open(sys.argv[1], encoding="utf-8")]
f = lambda x: "inf" if not math.isfinite(x) else f"{x:.3f}"

print("## L1\n\n| model | BI | warm | mode | N | calls | p50 (s) | p95 (s) | fail | n_seq | prompt tok |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
l1 = defaultdict(list)
for r in rows:
    if r["test"] == "L1":
        l1[(r["model"], r["bi"], r["mode"], r["N"], r.get("warm", "N1only"))].append(r)
p95 = {}
for k in sorted(l1):
    v = l1[k]
    lat = [r["lat"] for r in v]
    p95[k] = censored_quantile(lat, 0.95)
    fail = sum(x is None for x in lat)
    toks = Counter(r["input_tokens"] for r in v).most_common(1)[0][0]
    print(f"| {k[0]} | {k[1]} | {k[4]} | {k[2]} | {k[3]} | {len(v)} | {f(censored_quantile(lat, 0.5))} | {f(p95[k])} | "
          f"{fail} | {v[0]['n_seq']} | {toks} |")

print("\n## L1 판정 (N=4, BI=1)\n")
for m in sorted({k[0] for k in l1}):
    for mode in ("text", "image"):
        x = p95.get((m, 1, mode, 4, "perN"))
        if x is None:
            continue
        v = "target" if x <= 0.15 else ("acceptable" if x <= 0.33 else "fail")
        print(f"- {m} {mode}: p95 {f(x)} s -> {v}")

print("\n## L3 (N=4): p95(image) - p95(text)\n")
for m in sorted({k[0] for k in l1}):
    for bi in (0, 1):
        a, b = p95.get((m, bi, "image", 4, "perN")), p95.get((m, bi, "text", 4, "perN"))
        if a is not None and b is not None:
            print(f"- {m} BI={bi}: {f(a)} - {f(b)} = {f(a - b)} s")

print("\n## L2\n\n| model | BI | calls ok | payload flip (any q) | (payload,q) flip | max |Δp_chosen| |")
print("|---|---|---|---|---|---|")
l2 = defaultdict(list)
for r in rows:
    if r["test"] == "L2":
        l2[(r["model"], r["bi"])].append(r)
for k in sorted(l2):
    v = [r for r in l2[k] if r["ok"]]
    by = defaultdict(list)
    for r in v:
        by[r["payload"]].append(r)
    pf, qf, total_q, dmax = 0, 0, 0, 0.0
    for j, rs in by.items():
        anyflip = False
        for q in rs[0]["probs"]:
            ch = [r["answers"][q]["choice"] for r in rs]
            modal = Counter(ch).most_common(1)[0][0]
            total_q += 1
            if len(set(ch)) > 1:
                qf += 1
                anyflip = True
            ps = [r["probs"][q][modal] for r in rs]
            dmax = max(dmax, max(ps) - min(ps))
        pf += anyflip
    print(f"| {k[0]} | {k[1]} | {len(v)}/{len(l2[k])} | {pf}/{len(by)} | {qf}/{total_q} | {dmax:.2e} |")
