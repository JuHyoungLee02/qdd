"""Merge the Isaac settle check of task_items (validate_objects objects_check.json) into task_items.json.
Round / thin items (fruit, pens) roll about their own axis, so the tilt test of validate_objects does not apply:
  stable          the validate_objects verdict (tilt / drift / dz)
  stable_rolling  drift <= 30 mm and |dz| <= 40 mm (stays where it was put; rolling in place allowed)
Containers: gate_pass / gate_fits / gate_n / gate_inside from gate_containers (containers_check.json); rows
without a place target or not gated get gate_pass False.
usage: python tools/l8x_assets/mark_task_items.py task_items.json objects_check.json
       python tools/l8x_assets/mark_task_items.py --containers containers.json containers_check.json"""
from __future__ import annotations

import json
import sys


def mark_containers(cont_p, check_p):
    t = json.load(open(cont_p))
    chk = json.load(open(check_p))
    for k, c in t["containers"].items():
        g = chk.get(k) or {}
        c.update(gate_pass=bool(g.get("pass")), gate_fits=g.get("fits", []), gate_n=g.get("n", 0),
                 gate_inside=g.get("inside", 0), gate_hung=bool(g.get("hung")))
    json.dump(t, open(cont_p, "w"), indent=1)
    print(sum(c["gate_pass"] for c in t["containers"].values()), "/", len(t["containers"]), "pass")


def main(argv=None):
    args = argv or sys.argv[1:]
    if args[0] == "--containers":
        return mark_containers(args[1], args[2])
    items_p, check_p = args[:2]
    t = json.load(open(items_p))
    chk = json.load(open(check_p))
    for k, o in t["objects"].items():
        c = chk.get(k)
        o["stable"] = bool(c and c["stable"])
        o["stable_rolling"] = bool(c and c["drift_mm"] <= 30 and abs(c["dz_mm"]) <= 40)
        o["settle"] = c
    json.dump(t, open(items_p, "w"), indent=1)
    print({k: o["stable_rolling"] for k, o in t["objects"].items()})


if __name__ == "__main__":
    main()
