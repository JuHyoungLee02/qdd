"""Recompute the name fields of a real-object table after a noun-keyword change, without re-meshing: claimed noun
(source name, then source category) -> name_check -> size words -> task_name / name -> split (noun hash);
task_target_ok follows (stable and a checked noun). Everything else (geometry, stability, clutter flags) stays.
usage: python tools/l8x_assets/renoun.py TABLE.json"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import objects_real as OR  # noqa: E402
from tools.l8x_assets.real_table import split_of  # noqa: E402


def main(argv=None):
    a = argv or sys.argv[1:]
    t = json.load(open(a[0]))
    objs = t["objects"]
    changed = 0
    for o in objs.values():
        nc = OR.name_check(OR.claimed_noun(o["source_name"], o.get("category_src", "")), o)
        changed += nc["noun"] != o["noun"]
        o.update(name_check=nc, noun=nc["noun"], category=nc["noun"])
    sw = OR.size_words(objs)
    for k, o in objs.items():
        o["size_word"] = sw.get(k)
        o["task_name"] = o["name"] = OR.task_name(o, sw.get(k))
        o["split"] = split_of(o["noun"])
        if "stable" in o:
            o["task_target_ok"] = bool(o["stable"]) and o["noun"] not in ("object", "SKIP")
    with open(a[0], "w") as f:
        json.dump(t, f, indent=1)
    print("nouns changed", changed, "split", {s: sum(o["split"] == s for o in objs.values()) for s in ("train", "ood_o")})


if __name__ == "__main__":
    main()
