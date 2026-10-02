"""E-RC0 summary (prereg_rc0.md): per arm x split (Atomic-Seen / Composite-Seen / Composite-Unseen) success with Wilson
95 %, A - P paired on the same (task, k) with a task bootstrap, failure types, latency.
usage: summary.py [root=/data/harvest/out/rc0] (run with the robocasa venv: it reads the task sets)"""
import glob
import json
import math
import os
import sys
from collections import Counter

import numpy as np
from robocasa.utils.dataset_registry import TARGET_TASKS

root = sys.argv[1] if len(sys.argv) > 1 else "/data/harvest/out/rc0"
rows = [r for p in glob.glob(os.path.join(root, "*", "*", "k*", "row.json"))
        for r in [json.load(open(p))] if p.split(os.sep)[-4] == r["arm"]]  # skip kept invalid runs (A_v1)
split = {t: s for s, ts in TARGET_TASKS.items() for t in ts}


def wilson(k, n, z=1.96):
    if not n:
        return 0, 0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


md = ["# E-RC0 결과 (RoboCasa365 target 50과제 시범)", "", "| 묶음 | A 본 35B (무학습) | P 공식 π0.5 | A − P (짝) |",
      "|---|---|---|---|"]
by = {(r["arm"], r["task"], r["k"]): r["success"] for r in rows}
for s in ("atomic_seen", "composite_seen", "composite_unseen", "all"):
    cells = []
    for arm in ("A", "P"):
        rs = [r for r in rows if r["arm"] == arm and (s == "all" or split.get(r["task"]) == s)]
        k = sum(r["success"] for r in rs)
        lo, hi = wilson(k, len(rs))
        cells.append("-" if not rs else f"{k}/{len(rs)} = {k / len(rs) * 100:.0f} % [{lo * 100:.0f}–{hi * 100:.0f}]")
    keys = sorted({(t, k) for (a, t, k) in by if a == "A" and ("P", t, k) in by and (s == "all" or split.get(t) == s)})
    d = "-"
    if keys:
        tasks = sorted({t for t, _ in keys})
        per = {t: [float(by[("A", t, k)]) - float(by[("P", t, k)]) for (tt, k) in keys if tt == t] for t in tasks}
        v = np.mean([x for xs in per.values() for x in xs])
        rng = np.random.default_rng(0)
        bs = [np.mean([x for i in rng.integers(0, len(tasks), len(tasks)) for x in per[tasks[i]]]) for _ in range(10000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        d = f"{v * 100:+.1f} %p [{lo * 100:+.1f}, {hi * 100:+.1f}]"
    md.append(f"| {s} | " + " | ".join(cells) + f" | {d} |")
for arm in ("A", "P"):
    c = Counter((f"{r.get('end_reason')}/{r.get('fail_stage')}" if arm == "A" else r.get("end_reason"))
                for r in rows if r["arm"] == arm and not r["success"])
    lat = [x for r in rows if r["arm"] == arm for x in r.get("latency_s") or []]
    md.append(f"- {arm}: 실패 " + ", ".join(f"{k} {v}" for k, v in c.most_common(4))
              + (f"; 호출 중앙 {np.median(lat):.2f} s" if lat else ""))
open(os.path.join(root, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
