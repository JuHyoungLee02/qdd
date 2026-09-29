"""E-PT F2 verdicts (prereg_pt.md §5.2): per arm vs the L8-xyz baseline on DEV and OOD-H.
DEV non-inferiority: arm approach xy median <= baseline + 5 mm and valid >= 0.95 ('cannot separate' when both <= 10 mm).
OOD-H: primary = approach 3D error median; BETTER when arm <= 0.8 x baseline AND the paired bootstrap (10,000, seed 0)
95 % interval of the mean per-snapshot difference (arm - baseline) is below 0; SAME when it contains 0; WORSE when above.
Pairs = approach snapshots where both arms produced a goal; snapshots with a missing goal are counted per arm.
usage: python compare.py <eval root> <baseline tag> <arm tag> [<arm tag> ...]   (reads <root>/{dev,ood_h}_<tag>/)"""
import json
import os
import sys

import numpy as np


def load(root, s, tag):
    p = os.path.join(root, f"{s}_{tag}")
    sc = {json.loads(x)["id"]: json.loads(x) for x in open(os.path.join(p, "scores.jsonl"))}
    return sc, json.load(open(os.path.join(p, "summary.json")))["control_all"]


def boot(d, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    d = np.asarray(d, float)
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return [round(float(np.percentile(m, 2.5)), 1), round(float(np.percentile(m, 97.5)), 1)]


def paired(a, b, key, filt=lambda k: True):
    ks = [k for k in a if k in b and filt(k) and a[k].get(key) is not None and b[k].get(key) is not None]
    return ks, [a[k][key] - b[k][key] for k in ks]


root, base = sys.argv[1], sys.argv[2]
B = {s: load(root, s, base) for s in ("dev", "ood_h")}
out = {}
for tag in sys.argv[3:]:
    A = {s: load(root, s, tag) for s in ("dev", "ood_h")}
    r = {}
    ad, bd = A["dev"][1], B["dev"][1]
    ni = ad["valid_rate"] >= 0.95 and ad["approach_xy_median_mm"] <= bd["approach_xy_median_mm"] + 5
    r["dev"] = {"arm_xy": ad["approach_xy_median_mm"], "base_xy": bd["approach_xy_median_mm"],
                "arm_3d": ad.get("approach_3d_median_mm"), "base_3d": bd.get("approach_3d_median_mm"),
                "valid": ad["valid_rate"], "noninferior": bool(ni),
                "cannot_separate": ad["approach_xy_median_mm"] <= 10 and bd["approach_xy_median_mm"] <= 10}
    groups = (("both", lambda k: "tz0.82" in k or "tz0.88" in k), ("wide", lambda k: "tz0.78" in k or "tz0.92" in k),
              ("tz0.78", lambda k: "tz0.78" in k), ("tz0.82", lambda k: "tz0.82" in k), ("tz0.88", lambda k: "tz0.88" in k),
              ("tz0.92", lambda k: "tz0.92" in k))
    for name, f in groups:
        ks, d = paired(A["ood_h"][0], B["ood_h"][0], "approach_3d_mm", f)
        a3 = [A["ood_h"][0][k]["approach_3d_mm"] for k in ks]
        b3 = [B["ood_h"][0][k]["approach_3d_mm"] for k in ks]
        gz_a = [abs(A["ood_h"][0][k]["grasp_z_mm"]) for k in ks if A["ood_h"][0][k].get("grasp_z_mm") is not None]
        gz_b = [abs(B["ood_h"][0][k]["grasp_z_mm"]) for k in ks if B["ood_h"][0][k].get("grasp_z_mm") is not None]
        ci = boot(d) if d else None
        med_a, med_b = (float(np.median(a3)) if a3 else None), (float(np.median(b3)) if b3 else None)
        verdict = None
        if ci:
            verdict = "BETTER" if (med_a <= 0.8 * med_b and ci[1] < 0) else ("WORSE" if ci[0] > 0 else "SAME")
        r[f"ood_h_{name}"] = {"n_pairs": len(ks), "arm_3d_median": med_a, "base_3d_median": med_b,
                              "mean_diff_ci95": ci, "verdict": verdict,
                              "arm_grasp_absz_median": float(np.median(gz_a)) if gz_a else None,
                              "base_grasp_absz_median": float(np.median(gz_b)) if gz_b else None}
    oa = A["ood_h"][1]
    r["gap_3d"] = round(oa["approach_3d_median_mm"] / ad["approach_3d_median_mm"], 2) \
        if oa.get("approach_3d_median_mm") and ad.get("approach_3d_median_mm") else None
    r["ood_h_summary"] = {k: oa.get(k) for k in ("valid_rate", "approach_xy_median_mm", "approach_3d_median_mm",
                                                  "grasp_absz_median_mm", "grasp_absz_le15_share", "approach_move_share",
                                                  "est_table_mm_median", "est_tgt_h_mm_median")}
    out[tag] = r
print("COMPARE " + json.dumps(out))
