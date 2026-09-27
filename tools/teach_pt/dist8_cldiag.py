"""E-DIST8 closed-loop failure decomposition, one line per episode (measured, from result.json):
  perception  approach calls whose goal xy is > 20 mm from the target (and, for point answers, whether the resolved
              point landed on another object / table)
  target      first close: xy error to the target and TCP height vs the target top (grasp-z error)
  executor    clipped / blocked (timeout) move events
  grasp       close events, grasp_lift, holding after close; place: goal xy error to the place object while carrying
usage: python dist8_cldiag.py <closed root> [<closed root> ...]"""
import glob
import json
import os
import sys

import numpy as np

for root in sys.argv[1:]:
    for rp in sorted(glob.glob(os.path.join(root, "*", "*", "*", "result.json"))):
        r = json.load(open(rp))
        calls = [c for c in r["calls"] if c.get("attempt") == 0 and c.get("valid")]
        ap = [c for c in calls if c.get("phase_truth") == "approach" and c.get("score")]
        ca = [c for c in calls if c.get("phase_truth") == "carry" and c.get("score")]
        axy = [c["score"]["xy_err_mm"] for c in ap]
        cxy = [c["score"]["xy_err_mm"] for c in ca]
        kinds = {}
        for c in ap:
            k = (c.get("resolved") or {}).get("kind")
            if k:
                kinds[k] = kinds.get(k, 0) + 1
        ev = r["events"]
        fc = r.get("first_close") or {}
        out = {"ep": os.path.relpath(os.path.dirname(rp), root), "arm": os.path.basename(root.rstrip("/")),
               "success": r["success"], "fail_stage": r.get("fail_stage"), "grasp_lift": r.get("grasp_lift"),
               "n_calls": r["n_calls"],
               "approach_goal_xy_med": round(float(np.median(axy)), 1) if axy else None,
               "approach_far20": sum(v > 20 for v in axy), "n_approach": len(axy), "resolved": kinds,
               "carry_goal_xy_med": round(float(np.median(cxy)), 1) if cxy else None,
               "first_close_xy": fc.get("err_xy_mm"), "first_close_dz": fc.get("dz_mm", fc.get("err_z_mm")),
               "n_close": sum(e["event"] == "close" for e in ev), "n_open": sum(e["event"] == "open" for e in ev),
               "n_clipped": r.get("n_clipped"), "n_blocked": r.get("n_blocked"),
               "modes": {k: v for k, v in (r.get("modes") or {}).items() if v}}
        print(json.dumps(out))
