"""Spec for bake_open.py (articulated tasks A / B / C): the gate-passed drawer pieces (their highest drawer joint),
the gate-passed fridge (its door joint, 90 deg) and the THOR boxes of the flap gate (rest pose = flaps open).
usage: python tools/l8x_assets/bake_spec.py ARTICULATED_LIST.json BOX_GATE.json OUT.json"""
from __future__ import annotations

import json
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    lst = json.load(open(a[0]))["assets"]
    boxes = json.load(open(a[1]))
    spec = {}
    for n, r in sorted(lst.items()):
        dj = [j for j in r["joints"] if j["task"] == "drawer"]
        if dj:
            top = max(dj, key=lambda j: j.get("handle_z") or 0.0)
            spec[n] = {"usd": r["usd"], "joints": [top["joint"]], "max_rev_deg": None, "task": "A",
                       "split": r["split"]}
        fj = [j for j in r["joints"] if j["task"] == "fridge_door"]
        if fj:
            spec[n] = {"usd": r["usd"], "joints": [fj[0]["joint"]], "max_rev_deg": 90, "task": "B",
                       "split": r["split"]}
    for n, r in sorted(boxes.items()):
        if n.startswith("Box_") and r.get("spawn_ok") and all(j.get("ok") for j in r.get("joints", [])):
            # the rest pose (q = 0) is the OPEN box (flaps spread: 0.43 m wide vs 0.26 m with q at the limits)
            spec[n] = {"usd": r["usd"], "joints": [], "max_rev_deg": None, "task": "C", "split": "train"}
    json.dump(spec, open(a[2], "w"), indent=1)
    from collections import Counter
    print(len(spec), Counter(s["task"] for s in spec.values()))


if __name__ == "__main__":
    main()
