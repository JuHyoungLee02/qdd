"""E-DIST8 paired comparisons (prereg_dist8.md §4): arm X vs arm Y on the same states of one evaluation set, from the
two scores.jsonl files (harvest.teach_pt.evaluate). Metric: approach 3D error (mm) on approach snapshots where both
arms produced a goal; paired bootstrap 10,000, seed 0, of the mean per-snapshot difference (X - Y).
  verdict (Q1-Q3 rule): BETTER = upper < 0 and median_X <= 0.8 x median_Y; WORSE = lower > 0; else SAME
  noninferior(margin): upper <= margin (Q4: +2 mm for H vs D; max(5, 0.1 x median_R) for H-off vs R)
usage: python dist8_compare.py <name> <X eval dir> <Y eval dir> [margin_mm|r10]   -> one JSON line"""
import json
import os
import sys

import numpy as np


def load(d):
    return {json.loads(x)["id"]: json.loads(x) for x in open(os.path.join(d, "scores.jsonl"))}


def boot(v, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    v = np.asarray(v, float)
    m = v[rng.integers(0, len(v), (n, len(v)))].mean(1)
    return [round(float(np.percentile(m, 2.5)), 2), round(float(np.percentile(m, 97.5)), 2)]


name, dx, dy = sys.argv[1:4]
margin = sys.argv[4] if len(sys.argv) > 4 else None
X, Y = load(dx), load(dy)
ks = [k for k in X if k in Y and X[k].get("approach_3d_mm") is not None and Y[k].get("approach_3d_mm") is not None]
out = {"name": name, "x": dx, "y": dy, "n_pairs": len(ks)}
if ks:
    a = np.array([X[k]["approach_3d_mm"] for k in ks])
    b = np.array([Y[k]["approach_3d_mm"] for k in ks])
    ci = boot(a - b)
    ma, mb = float(np.median(a)), float(np.median(b))
    out.update(x_median=round(ma, 1), y_median=round(mb, 1), diff_ci95=ci,
               verdict="BETTER" if (ci[1] < 0 and ma <= 0.8 * mb) else ("WORSE" if ci[0] > 0 else "SAME"))
    if margin is not None:
        mg = max(5.0, 0.1 * mb) if margin == "r10" else float(margin)
        out.update(margin_mm=round(mg, 2), noninferior=bool(ci[1] <= mg))
    gz = lambda S: [abs(S[k]["grasp_z_mm"]) for k in ks if S[k].get("grasp_z_mm") is not None]
    ga, gb = gz(X), gz(Y)
    out.update(x_grasp_absz_le15=round(sum(v <= 15 for v in ga) / len(ga), 3) if ga else None,
               y_grasp_absz_le15=round(sum(v <= 15 for v in gb) / len(gb), 3) if gb else None)
print(json.dumps(out))
