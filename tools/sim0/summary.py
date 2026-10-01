"""E-SIM0 summary (prereg_sim0.md §4 = prereg_lib0.md §4 rules): per arm x task (coke by orientation, move near)
success with Wilson 95 %, A - B paired on the same episodes (bootstrap over episodes within the task, 10,000),
A within the standard step budget (80 steps = 26.7 s), failure types, latency.
usage: summary.py [root=/data/harvest/out/sim0] -> <root>/summary.{json,md}"""
from __future__ import annotations

import glob
import json
import math
import os
import sys
from collections import Counter

import numpy as np

GROUPS = {"coke (all)": lambda n: n.startswith("coke_"), "coke lr_switch": lambda n: n.startswith("coke_lr_switch"),
          "coke upright": lambda n: n.startswith("coke_upright"),
          "coke laid_vertically": lambda n: n.startswith("coke_laid_vertically"),
          "move near": lambda n: n.startswith("near_"), "all": lambda n: True}


def wilson(k, n, z=1.96):
    if not n:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)


BRIDGE_GROUPS = {"spoon on towel": lambda n: n.startswith("spoon_"), "carrot on plate": lambda n: n.startswith("carrot_"),
                 "stack blocks": lambda n: n.startswith("stack_"), "eggplant in basket": lambda n: n.startswith("eggplant_"),
                 "all": lambda n: True}


def main(root="/data/harvest/out/sim0"):
    global GROUPS
    rows = [json.load(open(p)) for p in glob.glob(os.path.join(root, "*", "*", "row.json"))]
    if any(r["ep"].startswith(("spoon_", "carrot_", "stack_", "eggplant_")) for r in rows):  # E-SIM1
        GROUPS = BRIDGE_GROUPS
    by = {(r["arm"], r["ep"]): r for r in rows}
    out, md = {}, [f"# {os.path.basename(root).upper()} 결과 (시범, 보고 전용)", "",
                   "| 묶음 | A 본 35B ep2.5 (무학습) | B π0.5 base (무학습) | A − B (짝) | A, 표준 걸음 예산 안 |", "|---|---|---|---|---|"]
    for g, f in GROUPS.items():
        cells = {}
        for arm in ("A", "B"):
            rs = [r for r in rows if r["arm"] == arm and f(r["ep"])]
            k = sum(r["success"] for r in rs)
            cells[arm] = {"n": len(rs), "k": k, "wilson": wilson(k, len(rs)),
                          "in_budget": sum(bool(r.get("success_in_budget")) for r in rs) if arm == "A" else None}
        keys = sorted({e for (a, e) in by if a == "A" and f(e)} & {e for (a, e) in by if a == "B" and f(e)})
        diff = None
        if keys:
            v = np.array([float(by[("A", e)]["success"]) - float(by[("B", e)]["success"]) for e in keys])
            rng = np.random.default_rng(0)
            bs = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(10000)]
            lo, hi = np.percentile(bs, [2.5, 97.5])
            d = v.mean()
            lab = "A better" if d >= 0.1 and lo > 0 else "B better" if d <= -0.1 and hi < 0 else "not separable"
            diff = {"n": len(keys), "pp": round(d * 100, 1), "ci": [round(lo * 100, 1), round(hi * 100, 1)], "label": lab}
        out[g] = dict(cells, diff=diff)

        def c(arm):
            x = cells[arm]
            if not x["n"]:
                return "-"
            return f"{x['k']}/{x['n']} = {x['k'] / x['n'] * 100:.0f} % [{x['wilson'][0] * 100:.0f}–{x['wilson'][1] * 100:.0f}]"
        ds = "-" if not diff else f"{diff['pp']:+.1f} %p [{diff['ci'][0]:+.1f}, {diff['ci'][1]:+.1f}] {diff['label']}"
        ib = "-" if not cells["A"]["n"] else str(cells["A"]["in_budget"])
        md.append(f"| {g} | {c('A')} | {c('B')} | {ds} | {ib} |")
    F = {arm: Counter((f"{r.get('end_reason')}/{r.get('fail_stage')}" if arm == "A" else r.get("end_reason"))
                      for r in rows if r["arm"] == arm and not r["success"]).most_common(6) for arm in ("A", "B")}
    L = {}
    for arm in ("A", "B"):
        lat = [x for r in rows if r["arm"] == arm for x in (r.get("latency_s") or [])]
        L[arm] = {"median_s": round(float(np.median(lat)), 3) if lat else None,
                  "p90_s": round(float(np.percentile(lat, 90)), 3) if lat else None,
                  "wall_median_s": round(float(np.median([r["wall_s"] for r in rows if r["arm"] == arm])), 1)
                  if any(r["arm"] == arm for r in rows) else None}
    md += ["", "## 실패 유형"] + [f"- {a}: " + ", ".join(f"{k} {v}" for k, v in F[a]) for a in F]
    md += ["", "## 지연"] + [f"- {a}: 호출/추론 중앙 {L[a]['median_s']} s, p90 {L[a]['p90_s']} s, 편당 벽시계 중앙 {L[a]['wall_median_s']} s"
                            for a in L]
    json.dump({"groups": out, "fail": F, "latency": L, "n_rows": len(rows)}, open(os.path.join(root, "summary.json"), "w"),
              indent=1)
    open(os.path.join(root, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:])
