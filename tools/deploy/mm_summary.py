"""E-DEP1 stage 1 summary (prereg_deploy1.md §1): per model and delta, paired with delta 0 on the same call site.
  python tools/deploy/mm_summary.py --rows <rows.jsonl> --out <dir with <model>/scores.jsonl>
Metrics: action_acc, approach_xy / carry_xy median (mm), point_px median; paired bootstrap (10,000, by call site) of
the change vs delta 0: action_acc drop (%p) and median xy increase (mm, approach + carry pooled).
Verdict per delta: SAFE (drop 95 % upper <= 2 %p and xy increase 95 % upper <= 2 mm), NEEDS_ROWS (drop 95 % lower
> 5 %p or xy increase 95 % lower > 5 mm), else GRAY; Delta* = the largest SAFE delta."""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np

DELTAS = (0.0, 0.5, 1.0, 2.0, 3.0)


def xy(s):
    v = s.get("approach_xy_mm")
    return v if v is not None else s.get("carry_xy_mm")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-boot", type=int, default=10000)
    a = ap.parse_args(argv)
    rows = {r["id"]: r for r in map(json.loads, open(a.rows))}
    rng = np.random.default_rng(0)
    res = {}
    for sp in sorted(glob.glob(os.path.join(a.out, "*", "scores.jsonl"))):
        name = os.path.basename(os.path.dirname(sp))
        sc = {s["id"]: s for s in map(json.loads, open(sp)) if s["id"] in rows}
        site = defaultdict(dict)  # (episode, call) -> delta -> score
        for i, s in sc.items():
            r = rows[i]
            site[(r["episode"], r["call"])][r["delta"]] = s
        out = {"n_sites": len(site)}
        for d in DELTAS:
            pairs = [(v[0.0], v[d]) for v in site.values() if 0.0 in v and d in v]
            if not pairs:
                continue
            acc0 = np.array([float(p[0]["action_ok"]) for p in pairs])
            accd = np.array([float(p[1]["action_ok"]) for p in pairs])
            xs = [(xy(p[0]), xy(p[1])) for p in pairs if xy(p[0]) is not None and xy(p[1]) is not None]
            x0 = np.array([u for u, _ in xs])
            xd = np.array([v for _, v in xs])
            px = [p[1]["point_px"] for p in pairs if p[1].get("point_px") is not None]
            n = len(pairs)
            drops, incs = [], []
            for _ in range(a.n_boot):
                k = rng.integers(0, n, n)
                drops.append((acc0[k].mean() - accd[k].mean()) * 100)
                if len(xs):
                    kk = rng.integers(0, len(xs), len(xs))
                    incs.append(np.median(xd[kk]) - np.median(x0[kk]))
            dl, dh = np.percentile(drops, [2.5, 97.5])
            il, ih = np.percentile(incs, [2.5, 97.5]) if incs else (np.nan, np.nan)
            if dh <= 2 and ih <= 2:
                v = "SAFE"
            elif dl > 5 or il > 5:
                v = "NEEDS_ROWS"
            else:
                v = "GRAY"
            mv = [rows[i]["moving_mm"] for i in sc if rows[i]["delta"] == d]
            out[str(d)] = {"n": n, "action_acc": round(float(accd.mean()), 4), "action_acc_d0": round(float(acc0.mean()), 4),
                           "drop_pp": round(float(np.mean(drops)), 2), "drop_ci": [round(float(dl), 2), round(float(dh), 2)],
                           "xy_med_mm": round(float(np.median(xd)), 1) if len(xd) else None,
                           "xy_med_d0_mm": round(float(np.median(x0)), 1) if len(x0) else None,
                           "xy_inc_ci": [round(float(il), 2), round(float(ih), 2)],
                           "point_px_med": round(float(np.median(px)), 1) if px else None,
                           "arm_offset_mm_med": round(float(np.median(mv)), 1) if mv else None, "verdict": v}
        safe = [d for d in DELTAS if out.get(str(d), {}).get("verdict") == "SAFE"]
        out["delta_star"] = max(safe) if safe else None
        res[name] = out
    json.dump(res, open(os.path.join(a.out, "summary_mm.json"), "w"), indent=1)
    print(json.dumps({k: {"delta_star": v["delta_star"],
                          **{d: [v[d]["action_acc"], v[d]["xy_med_mm"], v[d]["verdict"]] for d in map(str, DELTAS) if d in v}}
                      for k, v in res.items()}))


if __name__ == "__main__":
    main()
