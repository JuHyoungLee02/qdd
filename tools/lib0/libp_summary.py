"""E-LIBP summary (prereg_libp.md): per arm x perturbation category success (Wilson 95 %), Ab - each pi arm paired on the
same tasks (task bootstrap 10,000), per suite too. usage: libp_summary.py [root=/data/harvest/out/libp]"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from summary import wilson  # noqa: E402

root = sys.argv[1] if len(sys.argv) > 1 else "/data/harvest/out/libp"
meta = json.load(open(os.path.join(root, "meta.json")))
rows = [json.load(open(p)) for p in glob.glob(os.path.join(root, "*", "*", "t*_k*", "row.json"))]
ARMS = [a for a in ("Ab", "F", "R", "P0", "PF") if any(r["arm"] == a for r in rows)]
cat = lambda r: meta[f"{r['suite']}|{r['task']}"]["category"]
cats = sorted({m["category"] for m in meta.values()})
by = {(r["arm"], r["suite"], r["task"]): r["success"] for r in rows}
md = ["# E-LIBP 결과 (LIBERO-plus 시범, 보고 전용)", "", "| 범주 | " + " | ".join(ARMS) + " | Ab − R (짝) |",
      "|" + "---|" * (len(ARMS) + 2)]
out = {}
for c in cats + ["all"]:
    cells = []
    for a in ARMS:
        rs = [r for r in rows if r["arm"] == a and (c == "all" or cat(r) == c)]
        k = sum(r["success"] for r in rs)
        lo, hi = wilson(k, len(rs))
        out[f"{a}|{c}"] = {"k": k, "n": len(rs)}
        cells.append("-" if not rs else f"{k}/{len(rs)} = {k / len(rs) * 100:.0f} % [{lo * 100:.0f}–{hi * 100:.0f}]")
    keys = sorted({(s, t) for (a, s, t) in by if a == "Ab" and ("R", s, t) in by and (c == "all" or meta[f"{s}|{t}"]["category"] == c)})
    d = "-"
    if keys:
        v = np.array([float(by[("Ab",) + k]) - float(by[("R",) + k]) for k in keys])
        rng = np.random.default_rng(0)
        bs = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(10000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        d = f"{v.mean() * 100:+.1f} %p [{lo * 100:+.1f}, {hi * 100:+.1f}] (n={len(v)})"
    md.append(f"| {c} | " + " | ".join(cells) + f" | {d} |")
json.dump(out, open(os.path.join(root, "summary.json"), "w"), indent=1)
open(os.path.join(root, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
