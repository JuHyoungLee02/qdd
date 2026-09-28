"""Mark objects that moved in an Isaac clutter check (validate_clutter clutter_check.json) as clutter_ok false with the
reason; clutter.sample_clutter skips them.  usage: python tools/l8x_assets/mark_clutter_fail.py TABLE.json CHECK.json"""
from __future__ import annotations

import json
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    t = json.load(open(a[0]))
    n = 0
    for r in json.load(open(a[1])):
        for m in r["moved"]:
            o = t["objects"].get(m["id"])
            if o is not None and o.get("clutter_ok", True):
                o["clutter_ok"] = False
                o["clutter_fail"] = dict(m, scene=r["scene"])
                n += 1
    with open(a[0], "w") as f:
        json.dump(t, f, indent=1)
    print("marked", n)


if __name__ == "__main__":
    main()
