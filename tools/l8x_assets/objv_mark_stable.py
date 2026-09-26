"""Merge the Isaac settle check (validate_objects objects_check.json) into the object table: per object
stable_upright (bool, |bottom - top| <= 5 mm, tilt <= 10 deg, drift <= 2 cm after 2 s on a table) and settle
{dz_mm, drift_mm, tilt_deg}; objects never checked get stable_upright None.
usage: python tools/l8x_assets/objv_mark_stable.py TABLE.json CHECK.json [CHECK2.json ...]"""
from __future__ import annotations

import json
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    t = json.load(open(a[0]))
    chk = {}
    for p in a[1:]:
        chk.update(json.load(open(p)))
    n = {True: 0, False: 0, None: 0}
    for name, o in t["objects"].items():
        c = chk.get(name)
        o["stable_upright"] = None if c is None else bool(c["stable"])
        o["settle"] = None if c is None else {k: c[k] for k in ("dz_mm", "drift_mm", "tilt_deg")}
        n[o["stable_upright"]] += 1
    t["stable_rule"] = ("Isaac settle on a table (validate_objects): |bottom - top| <= 5 mm, tilt <= 10 deg, "
                        "drift <= 2 cm after 2 s; use stable_upright == True for upright task objects")
    with open(a[0], "w") as f:
        json.dump(t, f, indent=1)
    sp = {}
    for o in t["objects"].values():
        if o["stable_upright"]:
            sp[o["split"]] = sp.get(o["split"], 0) + 1
    print("stable", n[True], "unstable", n[False], "unchecked", n[None], "stable by split", sp)


if __name__ == "__main__":
    main()
