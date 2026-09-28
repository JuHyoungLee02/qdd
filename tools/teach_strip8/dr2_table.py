"""D round 2 closed-loop table: per arm and set (ood_h / ood_o), successes, grasp+lift, first-approach > 50 mm,
switches by guard, recheck answers (yes / no / unreadable) and re-asks. usage: python dr2_table.py <arm>=<root> [...]"""
import glob
import json
import os
import sys
from collections import Counter

for spec in sys.argv[1:]:
    arm, root = spec.split("=", 1)
    for s in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        rs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(root, s, "*", "s*", "result.json")))]
        if not rs:
            continue
        sw, rc, first = Counter(), Counter(), 0
        for r in rs:
            b = r.get("boost") or {}
            for x in b.get("switches", []):
                sw[x.get("guard", "above")] += 1
            for x in b.get("rechecks", []) or []:
                rc["yes" if x["answer"] is True else "no" if x["answer"] is False else "none"] += 1
                rc["reasked"] += bool(x.get("reasked"))
            ap = [c["score"]["xy_err_mm"] for c in r["calls"] if c.get("score") and
                  c["score"].get("xy_err_mm") is not None and c.get("phase_truth") == "approach"]
            first += bool(ap) and ap[0] > 50
        print(json.dumps({"arm": arm, "set": s, "n": len(rs), "success": sum(r["success"] for r in rs),
                          "grasp_lift": sum(bool(r.get("grasp_lift")) for r in rs), "first_gt50": first,
                          "switches": dict(sw), "rechecks": dict(rc),
                          "eps": " ".join(f"{r['seed']}:{int(r['success'])}{int(bool(r.get('grasp_lift')))}" for r in rs)}))
