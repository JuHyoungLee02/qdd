"""Stats of a real_table output: drop reasons (first word), unnamed objects' source names.
usage: python tools/l8x_assets/real_stats.py real_objects.json"""
from __future__ import annotations

import json
import sys
from collections import Counter


def main(argv=None):
    a = argv or sys.argv[1:]
    t = json.load(open(a[0]))
    c = Counter()
    for k, why in t["dropped"].items():
        for w in why.split("; "):
            c[k.split(":")[0] + ":" + w.split(" ")[0]] += 1
    print("drop reasons", c.most_common())
    un = [o["source_name"] for o in t["objects"].values() if o["noun"] == "object"]
    print("unnamed", len(un), un[:60])
    for n in a[1:]:
        print(n, [{k: o[k] for k in ("height", "grasp_width", "length", "circularity", "handle_ratio", "boxiness")}
                  for o in t["objects"].values() if o["source_name"] == n])
    print("renamed examples", [(o["source_name"], o["name_check"]["claimed"], o["noun"]) for o in t["objects"].values()
                               if o["name_check"]["renamed"] and o["name_check"]["claimed"]][:20])


if __name__ == "__main__":
    main()
