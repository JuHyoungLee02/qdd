"""boost1 / boost2 mechanism metrics per arm and set: carry-phase place-target xy error median (calls with a score
while carrying), episodes ending at the call cap, switches and memory resolves, first-approach error (target
identification: > 50 mm). usage: python boost_stats.py <arm>=<closed root> [...]"""
import glob
import json
import os
import sys

import numpy as np

for spec in sys.argv[1:]:
    arm, root = spec.split("=", 1)
    for s in ("ood_h", "ood_o"):
        rs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(root, s, "*", "s*", "result.json")))]
        if not rs:
            continue
        carry, first, caps, sw, mem = [], [], 0, 0, 0
        for r in rs:
            sc = [c for c in r["calls"] if c.get("score") and c["score"].get("xy_err_mm") is not None]
            carry += [c["score"]["xy_err_mm"] for c in sc if c.get("phase_truth") == "carry"]
            ap = [c["score"]["xy_err_mm"] for c in sc if c.get("phase_truth") == "approach"]
            first.append(ap[0] if ap else None)
            caps += r["end_reason"] == "stage_cap_calls"
            b = r.get("boost") or {}
            sw += len(b.get("switches", []))
            mem += b.get("n_memory_resolves", 0)
        print(json.dumps({"arm": arm, "set": s, "n": len(rs), "success": sum(r["success"] for r in rs),
                          "grasp_lift": sum(bool(r.get("grasp_lift")) for r in rs),
                          "carry_xy_median_mm": round(float(np.median(carry)), 1) if carry else None,
                          "n_carry_calls": len(carry), "cap_ends": caps, "switches": sw, "memory_resolves": mem,
                          "first_approach_gt50": sum(1 for f in first if f is not None and f > 50)}))
