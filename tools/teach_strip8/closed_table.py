"""One line per closed-loop episode: arm, set, seed, success, grasp_lift, fail stage, end reason, calls, t_success,
first-close xy (mm), approach-target xy median (mm). usage: python closed_table.py <arm>=<closed root> [...]"""
import glob
import json
import os
import sys

import numpy as np

for spec in sys.argv[1:]:
    arm, root = spec.split("=", 1)
    for rp in sorted(glob.glob(os.path.join(root, "*", "s*", "result.json"))):
        r = json.load(open(rp))
        xs = [c["score"]["xy_err_mm"] for c in r["calls"] if c.get("score") and c["score"].get("xy_err_mm") is not None
              and c.get("phase_truth") == "approach"]
        print(json.dumps({"arm": arm, "set": os.path.basename(os.path.dirname(os.path.dirname(rp))),
                          "seed": r["seed"], "success": r["success"], "grasp_lift": r.get("grasp_lift"),
                          "fail": r.get("fail_stage"), "end": r["end_reason"], "calls": r["n_calls"],
                          "t_success": r.get("t_success"),
                          "first_close_xy": (r.get("first_close") or {}).get("err_xy_mm"),
                          "approach_xy_med": round(float(np.median(xs)), 1) if xs else None}))
