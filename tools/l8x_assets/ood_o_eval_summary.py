"""Summary of the rendered OOD-O closed-loop eval set (ood_o_eval_plan.py): keeps only truth successes (episodes)
and lists truth failures apart; per episode seed / task / success /
skip / room / exposure, written next to the render as eval_list.json.
usage: python3 tools/l8x_assets/ood_o_eval_summary.py RENDER_DIR OUT.json"""
from __future__ import annotations

import glob
import json
import os
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    rows = []
    for p in sorted(glob.glob(os.path.join(a[0], "**", "meta.json"), recursive=True)):
        m = json.load(open(p))
        sp = os.path.join(os.path.dirname(p), "scene.json")
        sc = json.load(open(sp)) if os.path.exists(sp) else {}
        room = (sc.get("furniture") or {}).get("room") if isinstance(sc.get("furniture"), dict) else None
        if room is None:
            room = json.dumps(sc).split('"room": ')[1].split(",")[0].strip('"') if '"room": ' in json.dumps(sc) else None
        rows.append({"seed": m.get("seed"), "task": m.get("task"), "dir": os.path.relpath(os.path.dirname(p), a[0]),
                     "success": m.get("success"), "end_reason": m.get("end_reason"), "skipped": m.get("skipped"),
                     "room": room if isinstance(room, str) else (room or {}).get("name"),
                     "max_sat": m.get("max_sat"), "max_dq_rad": m.get("max_dq_rad"), "n_rows": m.get("n_rows"),
                     "style": m.get("style"), "n_perturb": m.get("n_perturb")})
    ok = [r for r in rows if r["success"]]  # the eval set = truth successes only (a truth failure caps the model)
    per = {}
    for r in ok:
        o = r["task"].split("__", 1)[1]
        per[o] = per.get(o, 0) + 1
    out = {"n_rendered": len(rows), "n": len(ok), "n_truth_fail": len(rows) - len(ok),
           "n_skipped": sum(bool(r["skipped"]) for r in rows), "per_object": dict(sorted(per.items())),
           "min_per_object": min(per.values()) if per else 0, "seeds": [r["seed"] for r in ok], "episodes": ok,
           "truth_fail": [r for r in rows if not r["success"]]}
    json.dump(out, open(a[1], "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("episodes", "truth_fail", "seeds")}))


if __name__ == "__main__":
    main()
