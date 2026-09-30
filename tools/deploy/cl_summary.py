"""E-DEP1 stage 2 summary (prereg_deploy1.md §2 + change 1). Paired by (variant, seed) against S0, bootstrap 10,000.
  python tools/deploy/cl_summary.py --out /data/harvest/out/deploy/cl1
Per arm: success, no-command time (s and share of sim time: the robot runs with no fresh upper command = waiting or
the adapter continuation; the OX stand-in for the 'JCR-alone' time), mid-episode stops / stopped time, dropped-answer
share, calls, per-call xy error of rest vs mid-motion calls (median). Adoption (OX stage, change 1): success lower 95 %
>= -5 %p vs S0, mid-motion xy median - rest xy median (pooled over the arm) <= 2 mm, no-command time >= 50 % below S0
and its share <= S0's; the JCR-alone non-inferiority is for the JCR stage."""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    E = defaultdict(dict)
    for p in glob.glob(os.path.join(a.out, "*", "*", "s*", "ep.json")):
        e = json.load(open(p))
        E[e["arm"]][(e["variant"], e["seed"])] = e
    rng = np.random.default_rng(0)
    base = E.get("S0", {})
    res = {}
    for arm, eps in sorted(E.items()):
        v = list(eps.values())
        xr = [x for e in v for x in e["xy_rest_mm"]]
        xm = [x for e in v for x in e["xy_mid_mm"]]
        nc = sum(e["n_calls"] for e in v)
        r = {"n": len(v), "success": round(float(np.mean([e["success"] for e in v])), 3),
             "no_cmd_s": round(float(np.mean([e["no_cmd_s"] for e in v])), 2),
             "no_cmd_share": round(float(np.mean([e["no_cmd_s"] / max(e["sim_t"] or 1, 1) for e in v])), 3),
             "stops": round(float(np.mean([e["continuity"]["stops"] for e in v])), 2),
             "stop_s": round(float(np.mean([e["continuity"]["stop_s"] for e in v])), 2),
             "dropped_share": round(sum(e["n_dropped"] for e in v) / max(nc, 1), 3),
             "calls": round(nc / max(len(v), 1), 1), "mid_calls": round(sum(e["n_mid"] for e in v) / max(len(v), 1), 1),
             "xy_rest_med": round(float(np.median(xr)), 1) if xr else None,
             "xy_mid_med": round(float(np.median(xm)), 1) if xm else None,
             "sim_t": round(float(np.mean([e["sim_t"] or 0 for e in v])), 1)}
        keys = sorted(set(eps) & set(base))
        if arm != "S0" and keys:
            d = np.array([float(eps[k]["success"]) - float(base[k]["success"]) for k in keys])
            bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(10000)]
            w0 = np.mean([base[k]["no_cmd_s"] for k in keys])
            w1 = np.mean([eps[k]["no_cmd_s"] for k in keys])
            r.update(d_success=round(float(d.mean()) * 100, 1), d_ci=[round(float(x) * 100, 1) for x in np.percentile(bs, [2.5, 97.5])],
                     no_cmd_cut=round(float(1 - w1 / max(w0, 1e-9)), 3))
            xy_ok = r["xy_mid_med"] is None or r["xy_rest_med"] is None or r["xy_mid_med"] - r["xy_rest_med"] <= 2
            r["adopt"] = bool(r["d_ci"][0] >= -5 and xy_ok and r["no_cmd_cut"] >= 0.5 and r["no_cmd_share"] <= res.get("S0", {}).get("no_cmd_share", 1))
        res[arm] = r
    json.dump(res, open(os.path.join(a.out, "summary_cl.json"), "w"), indent=1)
    print(json.dumps({k: {x: v.get(x) for x in ("n", "success", "d_success", "d_ci", "no_cmd_s", "no_cmd_cut", "stops",
                                                "dropped_share", "xy_rest_med", "xy_mid_med", "adopt")} for k, v in res.items()}))


if __name__ == "__main__":
    main()
