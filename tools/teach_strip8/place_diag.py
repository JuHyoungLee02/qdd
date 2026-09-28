"""Place-phase breakdown of closed-loop episodes: per carry call the resolved place target xy error (score), the target z
minus the true place top, memory use / drops and the command; the last 4 history lines. usage: python place_diag.py <ep dirs>"""
import json
import os
import sys

for ep in sys.argv[1:]:
    r = json.load(open(os.path.join(ep, "result.json")))
    print("==", os.path.basename(ep), r["end_reason"], "success", r["success"])
    for c in r["calls"]:
        if c.get("phase_truth") != "carry":
            continue
        cmd = (c.get("parsed") or {}).get("command") or {}
        res = c.get("resolved") or {}
        sc = c.get("score") or {}
        print(" call", c["call"], cmd.get("mode"), cmd.get("height"), cmd.get("gripper"), "xy_err", sc.get("xy_err_mm"),
              "goal", sc.get("goal"), "kind", res.get("kind"), "top", res.get("top"), "mem", res.get("memory"),
              "place_z_true", round(c["truth"]["place_xyz"][2], 3) if c.get("truth") else None)
    b = (r.get("boost") or {})
    print(" mem_drops", sum(1 for m in b.get("mem_checks", []) if not m["kept"]), "switches", b.get("switches"))
    for h in r["history"][-3:]:
        print("  |", h[:200])
