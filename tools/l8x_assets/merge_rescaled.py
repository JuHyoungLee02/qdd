"""Merge the settle-checked rescaled objects (rescale_real.py -> validate_objects -> objv_mark_stable) into
harvest/sim/assets_x/objects_real.json as NEW rows (existing rows untouched), and write the L8-D object gate plan
for them (ov_tray__<id>, seeds 35070-35072 = the L8-D real-object gate, table 0.85, objset x; the L8-D rule: >= 2 of
3 clean truth successes).
usage: python tools/l8x_assets/merge_rescaled.py RESCALED_CHECKED.json objects_real.json PLAN_OUT.json"""
from __future__ import annotations

import json
import sys

GATE_SEEDS = (35070, 35071, 35072)


def main(argv=None):
    a = argv or sys.argv[1:]
    new = json.load(open(a[0]))["objects"]
    t = json.load(open(a[1]))
    old = t["objects"]
    add = {k: r for k, r in new.items() if k not in old}
    if any(k in old for k in new):
        print("already merged:", sum(k in old for k in new))
    old.update(add)
    t.setdefault("rescaled", {"note": "gsor_* rows: GSO objects uniformly scaled to 8.5 cm tall (tools/l8x_assets/"
                                      "rescale_real.py, b4 / user-log 173); not their real size, no size word",
                              "n": 0})
    t["rescaled"]["n"] = sum(k.startswith("gsor_") for k in old)
    json.dump(t, open(a[1], "w"), indent=1)
    ok = sorted(k for k, r in old.items()
                if k.startswith("gsor_") and r.get("stable_upright") and r.get("task_target_ok"))
    plan = [{"seed": s, "split": "gate", "task": f"ov_tray__{k}", "variant": "standard", "table_z": 0.85,
             "objset": "x"} for k in ok for s in GATE_SEEDS]
    json.dump(plan, open(a[2], "w"), indent=0)
    by = {s: sum(old[k]["split"] == s for k in ok) for s in ("train", "ood_o")}
    print("added", len(add), "gate candidates", len(ok), by)


if __name__ == "__main__":
    main()
