"""E-H2H-T verdicts (prereg_h2h.md §3; E-PT 5.2 rule) on any evaluated split: per split, arm vs reference on the
approach 3D error (paired approach snapshots), median, paired bootstrap (10,000, seed 0) 95 % CI of the mean difference
(arm - ref): BETTER if arm median <= 0.8 x ref median and CI upper < 0; WORSE if CI lower > 0; else SAME.
Also valid rate, approach xy median, and the frame-leak count per arm.
usage: python -m xemb.h2h_compare EVAL_DIR OUT_JSON SPLIT_PREFIX[,...] REF ARM [ARM ...]
  eval dir holds <prefix><split>_<arm>/ (scores.jsonl, summary.json, leak.json); SPLIT_PREFIX like 'xood_h'."""
from __future__ import annotations

import json
import os
import sys

import numpy as np


def load(d):
    sc = {}
    for line in open(os.path.join(d, "scores.jsonl")):
        r = json.loads(line)
        sc[r["id"]] = r
    summ = json.load(open(os.path.join(d, "summary.json")))["control_all"]
    lk = os.path.join(d, "leak.json")
    leak = json.load(open(lk))["leak"] if os.path.exists(lk) else None
    return sc, summ, leak


def boot(d, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    d = np.asarray(d, float)
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return [round(float(np.percentile(m, 2.5)), 1), round(float(np.percentile(m, 97.5)), 1)]


def verdict(a, b):
    ks = [k for k in a if k in b and a[k].get("approach_3d_mm") is not None and b[k].get("approach_3d_mm") is not None]
    if not ks:
        return {"n_pairs": 0, "verdict": None}
    x = np.array([a[k]["approach_3d_mm"] for k in ks], float)
    y = np.array([b[k]["approach_3d_mm"] for k in ks], float)
    ci = boot(x - y)
    ma, mb = float(np.median(x)), float(np.median(y))
    v = "BETTER" if (ma <= 0.8 * mb and ci[1] < 0) else ("WORSE" if ci[0] > 0 else "SAME")
    return {"n_pairs": len(ks), "arm_3d_median": round(ma, 1), "ref_3d_median": round(mb, 1), "mean_diff_ci95": ci,
            "verdict": v}


def main(ev, outp, prefixes, ref, arms):
    res = {}
    for p in prefixes.split(","):
        rd = os.path.join(ev, f"{p}_{ref}")
        if not os.path.exists(os.path.join(rd, "summary.json")):
            continue
        R = load(rd)
        row = {"ref": ref, "ref_summary": {k: R[1].get(k) for k in ("n", "valid_rate", "approach_xy_median_mm",
                                                                        "approach_3d_median_mm")}, "ref_leak": R[2]}
        for arm in arms:
            ad = os.path.join(ev, f"{p}_{arm}")
            if not os.path.exists(os.path.join(ad, "summary.json")):
                row[arm] = "미완"
                continue
            A = load(ad)
            row[arm] = dict(verdict(A[0], R[0]), valid=A[1].get("valid_rate"), xy_median=A[1].get("approach_xy_median_mm"),
                            leak=A[2])
        res[p] = row
    json.dump(res, open(outp, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
