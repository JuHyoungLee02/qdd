"""Jev-L model selection summary (jevl_model_select.md prereg): accuracy A with episode-cluster bootstrap CI, paired
difference, per-question accuracy, ECE (15 bins), AUROC of p_chosen, NONE_ESCALATE rate.

usage: python jevl_select_report.py acc_A.jsonl acc_B.jsonl   (difference = A - B)
"""
import json
import sys
from collections import defaultdict

import numpy as np

from harvest.analysis.stats import auroc, cluster_bootstrap_ci, ece

files = sys.argv[1:3]
rows = {}
for f in files:
    rs = [json.loads(x) for x in open(f, encoding="utf-8")]
    rows[rs[0]["model"]] = {(r["snap"], r["qid"]): r for r in rs}
names = list(rows)
common = sorted(set(rows[names[0]]) & set(rows[names[1]]))
mean = lambda xs: float(np.mean(xs))
print(f"items paired: {len(common)} (per model: {[len(rows[m]) for m in names]}), "
      f"snapshots: {len({k[0] for k in common})}")


def clusters(model, fn, keys=common):
    by = defaultdict(list)
    for k in keys:
        r = rows[model][k]
        by[(r["kind"], r["seed"])].append(fn(r))
    return by


print("\n| model | A | 95% CI | ECE | AUROC | NONE_ESCALATE | errors |\n|---|---|---|---|---|---|---|")
for m in names:
    rs = [rows[m][k] for k in common]
    ok = [r["correct"] for r in rs]
    lo, hi = cluster_bootstrap_ci(clusters(m, lambda r: r["correct"]), mean)
    p = [r["p_chosen"] if r["p_chosen"] is not None else 0.0 for r in rs]
    au = auroc(p, ok)
    print(f"| {m} | {mean(ok):.4f} | [{lo:.4f}, {hi:.4f}] | {ece(p, ok):.4f} | "
          f"{au if au is None else round(au, 4)} | {mean([r['ne'] for r in rs]):.4f} | "
          f"{sum(r['error'] is not None for r in rs)} |")

a, b = names
by = defaultdict(list)
for k in common:
    ra, rb = rows[a][k], rows[b][k]
    by[(ra["kind"], ra["seed"])].append(int(ra["correct"]) - int(rb["correct"]))
d = mean([v for vs in by.values() for v in vs])
lo, hi = cluster_bootstrap_ci(by, mean)
print(f"\npaired difference {a} - {b}: {d:+.4f}, 95% CI [{lo:+.4f}, {hi:+.4f}] "
      f"({len(by)} episode clusters, 10,000 resamples) -> lower bound > 0: {lo > 0}; upper bound < 0: {hi < 0}")

qs = sorted({k[1].split(".")[-1] for k in common}, key=lambda q: ["dir_xy", "dir_z", "mag_coarse", "target", "phase",
                                                                     "progress"].index(q))
print("\n| question | n | " + " | ".join(f"{m} acc | {m} ECE | {m} AUROC | {m} NE" for m in names) + " | diff (CI) |")
print("|---|---|" + "---|---|---|---|" * len(names) + "---|")
for q in qs:
    keys = [k for k in common if k[1].split(".")[-1] == q]
    cells = []
    for m in names:
        rs = [rows[m][k] for k in keys]
        ok = [r["correct"] for r in rs]
        p = [r["p_chosen"] if r["p_chosen"] is not None else 0.0 for r in rs]
        au = auroc(p, ok)
        cells.append(f"{mean(ok):.3f} | {ece(p, ok):.3f} | {'-' if au is None else f'{au:.3f}'} | "
                     f"{mean([r['ne'] for r in rs]):.3f}")
    byq = defaultdict(list)
    for k in keys:
        byq[(rows[a][k]["kind"], rows[a][k]["seed"])].append(int(rows[a][k]["correct"]) - int(rows[b][k]["correct"]))
    l2, h2 = cluster_bootstrap_ci(byq, mean)
    print(f"| {q} | {len(keys)} | " + " | ".join(cells) +
          f" | {mean([v for vs in byq.values() for v in vs]):+.3f} [{l2:+.3f}, {h2:+.3f}] |")

print("\n| question | oracle key distribution |\n|---|---|")
for q in qs:
    c = defaultdict(int)
    for k in common:
        if k[1].split(".")[-1] == q:
            c[rows[a][k]["oracle"]] += 1
    print(f"| {q} | " + ", ".join(f"{kk} {v}" for kk, v in sorted(c.items(), key=lambda kv: -kv[1])) + " |")

print("\n| question | " + " | ".join(f"{m} chosen keys" for m in names) + " |\n|---|" + "---|" * len(names))
for q in qs:
    cells = []
    for m in names:
        c = defaultdict(int)
        for k in common:
            if k[1].split(".")[-1] == q:
                c[rows[m][k]["key"]] += 1
        cells.append(", ".join(f"{kk} {v}" for kk, v in sorted(c.items(), key=lambda kv: -kv[1])))
    print(f"| {q} | " + " | ".join(cells) + " |")

print("\n| kind | " + " | ".join(names) + " |\n|---|" + "---|" * len(names))
for kind in ("P0", "P1", "P2"):
    keys = [k for k in common if rows[a][k]["kind"] == kind]
    print(f"| {kind} | " + " | ".join(f"{mean([rows[m][k]['correct'] for k in keys]):.4f}" for m in names) + " |")
