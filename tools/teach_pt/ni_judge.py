"""Common L8-X non-inferiority judge (user-log 186): median and >20 mm failure rate instead of the mean, margins
calibrated from A/A pairs (same training file, different --seed).

Per L8-X set, over approach snapshots (evaluate.py scores with approach_row true):
  err  = approach_3d_mm, or 1e6 mm when the reply gave no goal (counts as a failure)
  median = median of err; fail = share of err > 20 mm
A/A margin per set and metric: every A/A pair (seed 0 vs seed 1 of one arm) gives a paired bootstrap distribution
  (10,000, seed 0) of the metric difference; the distributions of all pairs are pooled, sign-symmetrised (the seed
  labels are arbitrary) and the margin is the 95th percentile of |difference| (= the 95 % A/A range).
Judge X vs Y (seeds pooled as (seed, state) pairs): paired bootstrap of X - Y per set and metric; non-inferior when the
  upper 95 % bound <= the A/A margin, for both median and fail; a set is worse when either fails.
usage: python ni_judge.py aa <out json> <eval dir s0> <eval dir s1> [...more pairs]
       python ni_judge.py judge <margins json> <out json> <X dirs comma list> <Y dirs comma list>
         (X / Y dirs in the same seed order; each dir holds x_<set>_d-min_clean/scores.jsonl)"""
import json
import os
import sys

import numpy as np

XSETS = ("dev", "ood_h", "ood_d", "ood_o", "ood_s", "ood_t", "ood_hl")
FAIL_MM = 20.0
NO_GOAL_MM = 1e6  # a reply without a goal: a failure, finite so median differences stay defined
N_BOOT = 10000


def load_errs(d, xs):
    out = {}
    for x in open(os.path.join(d, f"x_{xs}_d-min_clean", "scores.jsonl")):
        r = json.loads(x)
        if r.get("approach_row"):
            e = r.get("approach_3d_mm")
            out[r["id"]] = float(e) if e is not None else NO_GOAL_MM
    return out


def stats(e):
    e = np.asarray(e, float)
    return float(np.median(e)), float(np.mean(e > FAIL_MM))


def paired(dx, dy, xs):
    """(X errs, Y errs) over the pooled (seed, state) pairs; dx / dy are dir lists in the same seed order."""
    a, b = [], []
    for x, y in zip(dx, dy):
        X, Y = load_errs(x, xs), load_errs(y, xs)
        ks = sorted(k for k in X if k in Y)
        a += [X[k] for k in ks]
        b += [Y[k] for k in ks]
    return np.asarray(a), np.asarray(b)


def boot(a, b, n=N_BOOT, seed=0):
    """-> (n, 2) array of [median diff, fail diff] over paired resamples."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), (n, len(a)))
    A, B = a[idx], b[idx]
    med = np.median(A, 1) - np.median(B, 1)
    fail = (A > FAIL_MM).mean(1) - (B > FAIL_MM).mean(1)
    return np.stack([med, fail], 1)


def aa(outp, dirs):
    res = {"rule": "user-log 186", "fail_mm": FAIL_MM, "pairs": [[d0, d1] for d0, d1 in zip(dirs[::2], dirs[1::2])],
           "sets": {}}
    for xs in XSETS:
        dist, per = [], []
        for d0, d1 in zip(dirs[::2], dirs[1::2]):
            a, b = paired([d1], [d0], xs)
            bt = boot(a, b)
            dist.append(np.abs(bt))
            m1, f1 = stats(a)
            m0, f0 = stats(b)
            per.append({"median_diff": round(m1 - m0, 2), "fail_diff": round(f1 - f0, 4), "n": len(a)})
        q = np.percentile(np.concatenate(dist), 95, axis=0)
        res["sets"][xs] = {"median_margin_mm": round(float(q[0]), 2), "fail_margin": round(float(q[1]), 4),
                           "pairs": per}
    json.dump(res, open(outp, "w"), indent=1)
    return res


def judge(margins, outp, dx, dy):
    M = json.load(open(margins))["sets"]
    res = {"x": dx, "y": dy, "sets": {}, "worse_sets": []}
    for xs in XSETS:
        a, b = paired(dx, dy, xs)
        bt = boot(a, b)
        (mx, fx), (my, fy) = stats(a), stats(b)
        lo, hi = np.percentile(bt, 2.5, axis=0), np.percentile(bt, 97.5, axis=0)
        ok_m = bool(hi[0] <= M[xs]["median_margin_mm"])
        ok_f = bool(hi[1] <= M[xs]["fail_margin"])
        res["sets"][xs] = {"n_pairs": len(a), "median_x": round(mx, 2), "median_y": round(my, 2),
                           "median_diff_ci95": [round(float(lo[0]), 2), round(float(hi[0]), 2)],
                           "fail_x": round(fx, 4), "fail_y": round(fy, 4),
                           "fail_diff_ci95": [round(float(lo[1]), 4), round(float(hi[1]), 4)],
                           "median_margin_mm": M[xs]["median_margin_mm"], "fail_margin": M[xs]["fail_margin"],
                           "noninferior": ok_m and ok_f}
        if not (ok_m and ok_f):
            res["worse_sets"].append(xs)
    res["noninferior_all"] = not res["worse_sets"]
    json.dump(res, open(outp, "w"), indent=1)
    return res


if __name__ == "__main__":
    if sys.argv[1] == "aa":
        r = aa(sys.argv[2], sys.argv[3:])
        print(json.dumps({k: {"median_margin_mm": v["median_margin_mm"], "fail_margin": v["fail_margin"]}
                          for k, v in r["sets"].items()}))
    else:
        r = judge(sys.argv[2], sys.argv[3], sys.argv[4].split(","), sys.argv[5].split(","))
        print(json.dumps({"noninferior_all": r["noninferior_all"], "worse_sets": r["worse_sets"]}))
