"""boost1b summary per arm (<mem>_<perturb>) and height set: successes, grasp+lift, memory drops, checks, carry target
error median; plus per-episode lines for the regression. usage: python b1b_table.py <boost1b out> [<boost1 after>]"""
import glob
import json
import os
import sys

import numpy as np

root = sys.argv[1]
extra = sys.argv[2] if len(sys.argv) > 2 else None
arms = sorted(d for d in os.listdir(root) if d != "vid_src" and os.path.isdir(os.path.join(root, d)))
if extra:
    arms.append("img_none(boost1)")
for a in arms:
    base = extra if a.startswith("img_none(") else os.path.join(root, a)
    for s in ("ood_h", "ood_o"):
        rs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(base, s, "*", "s*", "result.json")))]
        if not rs:
            continue
        carry, drops, checks, eps = [], 0, 0, []
        for r in rs:
            carry += [c["score"]["xy_err_mm"] for c in r["calls"] if c.get("score") and
                      c["score"].get("xy_err_mm") is not None and c.get("phase_truth") == "carry"]
            b = r.get("boost") or {}
            mc = b.get("mem_checks") or []
            calls = {m["call"] for m in mc}
            checks += len(calls)
            drops += len({m["call"] for m in mc if not m["kept"]})
            eps.append(f"{r['seed']}:{int(r['success'])}")
        print(json.dumps({"arm": a, "set": s, "n": len(rs), "success": sum(r["success"] for r in rs),
                          "grasp_lift": sum(bool(r.get("grasp_lift")) for r in rs), "checked_calls": checks,
                          "drops": drops, "carry_xy_med": round(float(np.median(carry)), 1) if carry else None,
                          "eps": " ".join(eps)}))
