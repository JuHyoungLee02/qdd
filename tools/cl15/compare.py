"""E-CL15 three-arm comparison on the 10 T1 episodes (prereg_cl15.md change 5): ep1.5 (out/cl15), base35 (out/cl15b
+ out/cl15d), astra (out/cl15c + out/cl15d); per episode success, calls, wall clock, median call latency, Astra KRW,
failure, mp4. An episode without a result: 'not run (cost cap)' when the Astra budget stop / gate fired, else
'not run'. -> /data/harvest/out/cl15d/compare.{json,md}"""
from __future__ import annotations

import json
import math
import os
import statistics

T1 = "/data/harvest/out/cl15/t1.json"
ARMS = [("ep1.5", ["/data/harvest/out/cl15"], "ep1.5"),
        ("base35", ["/data/harvest/out/cl15b", "/data/harvest/out/cl15d"], "base35"),
        ("astra", ["/data/harvest/out/cl15c", "/data/harvest/out/cl15d"], "astra")]
OUT = "/data/harvest/out/cl15d"
CAP_FILES = ["/data/harvest/out/cl15d/STOP_astra", "/data/harvest/out/cl15c/STOP"]


def wilson(k, n, z=1.96):
    if not n:
        return None
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def one(roots, ck, name):
    for root in roots:
        od = os.path.join(root, "res", ck, "none", "t1", name)
        p = os.path.join(od, "result.json")
        if os.path.exists(p):
            d = json.load(open(p))
            lat = [c["latency_s"] for c in d.get("calls") or [] if c.get("latency_s") is not None]
            cl = json.load(open(os.path.join(od, "cl.json"))) if os.path.exists(os.path.join(od, "cl.json")) else {}
            return {"status": "run", "success": bool(d.get("success")), "n_calls": d.get("n_calls"),
                    "wall_s": d.get("wall_s"), "lat_med_s": round(statistics.median(lat), 2) if lat else None,
                    "cost_krw": round(float(d.get("cost_krw") or 0), 1), "fail": None if d.get("success") else
                    f"{d.get('fail_stage')}/{d.get('end_reason')}", "mp4": cl.get("mp4"), "root": root}
    return None


def main():
    kinds = json.load(open(T1))["kinds"]
    capped = any(os.path.exists(f) for f in CAP_FILES)
    rows = []
    for k in sorted(kinds):
        v = kinds[k]
        name = f"{v['task']}_s{v['seed']}"
        for arm, roots, ck in ARMS:
            r = one(roots, ck, name) or {"status": "not run (cost cap)" if arm == "astra" and capped else "not run"}
            rows.append(dict(r, kind=k, arm=arm, task=v["task"], seed=v["seed"]))
    agg = {}
    for arm, _, _ in ARMS:
        rr = [r for r in rows if r["arm"] == arm and r["status"] == "run"]
        k = sum(r["success"] for r in rr)
        agg[arm] = {"n": len(rr), "success": k, "wilson95": wilson(k, len(rr)),
                    "krw": round(sum(r.get("cost_krw") or 0 for r in rr), 1),
                    "wall_med_s": statistics.median([r["wall_s"] for r in rr if r.get("wall_s")]) if rr else None,
                    "lat_med_s": statistics.median([r["lat_med_s"] for r in rr if r.get("lat_med_s")]) if rr else None}
    json.dump({"agg": agg, "rows": rows}, open(os.path.join(OUT, "compare.json"), "w"), indent=1)
    cell = lambda r: (r["status"] if r["status"] != "run" else  # noqa: E731
                      f"{'O' if r['success'] else 'X'} {r['n_calls']}c {r['wall_s']}s {r['lat_med_s']}s"
                      + (f" {r['cost_krw']:.0f}원" if r["arm"] == "astra" else "")
                      + ("" if r["success"] else f" ({r['fail']})"))
    md = ["| task | ep1.5 | base35 | astra |", "|---|---|---|---|"]
    for k in sorted(kinds):
        c = {r["arm"]: cell(r) for r in rows if r["kind"] == k}
        md.append(f"| {k} | {c['ep1.5']} | {c['base35']} | {c['astra']} |")
    md += ["", "| arm | success / run | Wilson 95 % | wall median s | call latency median s | KRW |", "|---|---|---|---|---|---|"]
    for arm, a in agg.items():
        md.append(f"| {arm} | {a['success']}/{a['n']} | {a['wilson95']} | {a['wall_med_s']} | {a['lat_med_s']} | {a['krw']} |")
    md.append("\ncell = O/X success, calls, wall clock per episode, median call latency, (Astra KRW), (failure)")
    open(os.path.join(OUT, "compare.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
