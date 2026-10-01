"""E-LIB0 summary (docs/stage3/prereg_lib0.md §4, rules fixed before the results): per arm x suite success rate with
Wilson 95 % CI, A - B paired difference (same episodes) with a task-level bootstrap (10,000) 95 % CI and the label
(A better: diff >= +10 pp and CI low > 0; B better: mirrored; else not separable), A's success within the openpi step
budget, failure types (A: end_reason x fail_stage; B / R: max_steps / exception), latency per call / infer.
usage: summary.py [out root=/data/harvest/out/lib0]  -> <root>/summary.json, summary.md"""
from __future__ import annotations

import glob
import json
import math
import os
import sys
from collections import Counter

import numpy as np

SUITES = ("libero_spatial", "libero_object", "libero_goal", "libero_10")
SHORT = {"libero_spatial": "Spatial", "libero_object": "Object", "libero_goal": "Goal", "libero_10": "Long"}
ARMS = ("A", "Ab", "B", "R")


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)


def rows_of(root: str) -> list:
    out = []
    for p in glob.glob(os.path.join(root, "*", "*", "t*_k*", "row.json")):
        out.append(json.load(open(p)))
    return out


def paired(rows: list, suites) -> dict:
    a = {(r["suite"], r["task"], r["k"]): r["success"] for r in rows if r["arm"] == "A" and r["suite"] in suites}
    b = {(r["suite"], r["task"], r["k"]): r["success"] for r in rows if r["arm"] == "B" and r["suite"] in suites}
    keys = sorted(set(a) & set(b))
    if not keys:
        return {"n": 0}
    tasks = sorted({k[:2] for k in keys})
    by = {t: [float(a[k]) - float(b[k]) for k in keys if k[:2] == t] for t in tasks}
    diff = float(np.mean([float(a[k]) - float(b[k]) for k in keys]))
    rng = np.random.default_rng(0)
    boots = []
    for _ in range(10000):
        pick = rng.integers(0, len(tasks), len(tasks))
        v = [x for i in pick for x in by[tasks[i]]]
        boots.append(np.mean(v))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    lab = ("A better" if diff >= 0.10 and lo > 0 else "B better" if diff <= -0.10 and hi < 0 else "not separable")
    return {"n": len(keys), "diff_pp": round(diff * 100, 1), "ci_pp": [round(lo * 100, 1), round(hi * 100, 1)],
            "label": lab}


def main(root: str = "/data/harvest/out/lib0"):
    rows = rows_of(root)
    S = {}
    for arm in ARMS:
        for s in SUITES + ("all",):
            rs = [r for r in rows if r["arm"] == arm and (s == "all" or r["suite"] == s)]
            k = sum(r["success"] for r in rs)
            d = {"n": len(rs), "k": k, "rate": round(k / len(rs), 3) if rs else None, "wilson": wilson(k, len(rs))}
            if arm in ("A", "Ab"):
                kb = sum(bool(r.get("success_in_budget")) for r in rs)
                d["in_budget"] = {"k": kb, "rate": round(kb / len(rs), 3) if rs else None}
            S[f"{arm}|{s}"] = d
    P = {s: paired(rows, (s,)) for s in SUITES}
    P["all"] = paired(rows, SUITES)
    F = {}
    for arm in ARMS:
        c = Counter()
        for r in rows:
            if r["arm"] != arm or r["success"]:
                continue
            c[f"{r.get('end_reason')}/{r.get('fail_stage')}" if arm in ("A", "Ab") else r.get("end_reason")] += 1
        F[arm] = c.most_common()
    LAT = {}
    for arm in ARMS:
        lat = [x for r in rows if r["arm"] == arm for x in (r.get("latency_s") or [])]
        calls = [r.get("n_calls") if arm in ("A", "Ab") else r.get("n_infer") for r in rows if r["arm"] == arm]
        wall = [r["wall_s"] for r in rows if r["arm"] == arm]
        LAT[arm] = {"n_lat": len(lat), "median_s": round(float(np.median(lat)), 3) if lat else None,
                    "p90_s": round(float(np.percentile(lat, 90)), 3) if lat else None,
                    "calls_median": float(np.median([c for c in calls if c is not None])) if calls else None,
                    "wall_median_s": round(float(np.median(wall)), 1) if wall else None}
    out = {"stats": S, "paired_A_minus_B": P, "fail_types": F, "latency": LAT, "n_rows": len(rows)}
    json.dump(out, open(os.path.join(root, "summary.json"), "w"), indent=1)

    def cell(arm, s):
        d = S[f"{arm}|{s}"]
        if not d["n"]:
            return "-"
        return f"{d['k']}/{d['n']} = {d['rate'] * 100:.0f} % [{d['wilson'][0] * 100:.0f}–{d['wilson'][1] * 100:.0f}]"
    md = ["# E-LIB0 결과 (시범, 보고 전용)", "",
          "| 묶음 | A 본 35B ep2.5 (무학습) | Ab = A + 어댑터 고침 (E-LIB0b) | B π0.5 base (무학습) | A − B (짝, 과제 부트스트랩) | 참고 R π0.5-LIBERO (LIBERO 미세조정) | A, openpi 걸음 예산 안 |",
          "|---|---|---|---|---|---|---|"]
    for s in SUITES + ("all",):
        p = P[s]
        pd = "-" if not p.get("n") else f"{p['diff_pp']:+.1f} %p [{p['ci_pp'][0]:+.1f}, {p['ci_pp'][1]:+.1f}] {p['label']}"
        ib = S[f"A|{s}"].get("in_budget") or {}
        ibs = "-" if ib.get("rate") is None else f"{ib['k']} ({ib['rate'] * 100:.0f} %)"
        md.append(f"| {SHORT.get(s, '전체')} | {cell('A', s)} | {cell('Ab', s)} | {cell('B', s)} | {pd} | {cell('R', s)} | {ibs} |")
    md += ["", "## 실패 유형 (상위)"]
    for arm in ARMS:
        md.append(f"- {arm}: " + ", ".join(f"{k} {v}" for k, v in F[arm][:5]))
    md += ["", "## 지연"]
    for arm in ARMS:
        d = LAT[arm]
        md.append(f"- {arm}: 호출/추론당 중앙 {d['median_s']} s, p90 {d['p90_s']} s (n={d['n_lat']}), "
                  f"편당 호출/추론 중앙 {d['calls_median']}, 편당 벽시계 중앙 {d['wall_median_s']} s")
    open(os.path.join(root, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:])
