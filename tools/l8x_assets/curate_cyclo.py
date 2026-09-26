"""cyclo_lab (Apache-2.0) tables and baskets: usd_import --mode declared output -> harvest/sim/assets_x/assets_cyclo.json.
Category, yaw (long side along y, facing the robot) and use are set per piece after looking at the rendered frames;
too few pieces for an OOD hold-out, so every piece is split "train".
usage: python tools/l8x_assets/curate_cyclo.py RAW.json OUT.json"""
from __future__ import annotations

import json
import math
import sys

LICENSE = "Apache-2.0"
SOURCE = "ROBOTIS-GIT/cyclo_lab @42dcd82 source/cyclo_lab/data/object"
DROP_REASON = {"plastic_basket2": "inner floor split by a divider into halves narrower than the open fingers "
                                  "(107 mm) + margin (render check c1, region reason obstacle / small)"}
PIECES = {  # name -> (category, top kind, yaw)
    "robotis_aiworker_table": ("work_table", "table", math.pi / 2),
    "robotis_net_table": ("work_table", "table", 0.0),
    "robotis_omy_table": ("work_table", "table", 0.0),
    "plastic_basket": ("basket", "bin_floor", 0.0),
    "plastic_basket2": ("basket", "bin_floor", math.pi / 2),
}


def curate(raw: dict, drop=()) -> dict:
    keep, dropped = {}, {}
    for name, r in sorted(raw.items()):
        if name not in PIECES or name in drop or "error" in r:
            dropped[name] = r.get("error", "not listed" if name not in PIECES else DROP_REASON.get(name, "dropped"))
            continue
        cat, kind, yaw = PIECES[name]
        keep[name] = {"tag": "cyclo", "category": cat, "top_kind": kind, "yaw": yaw, "dst": r["dst"], "src": r["src"],
                      "collider_size": r["collider_size"], "render_size": r["render_size"],
                      "origin_offset": r["origin_offset"], "render_vs_collider_mm": r["render_vs_collider_mm"],
                      "n_colliders": r["n_colliders"], "surfaces": [s for s in r["surfaces"] if s["top_z"] > 0.005],
                      "split": "train", "license": LICENSE, "source": SOURCE}
    return {"license": LICENSE, "source": SOURCE, "assets": keep, "dropped": dropped}


def main(argv=None):
    a = argv or sys.argv[1:]
    t = curate(json.load(open(a[0])), drop=tuple(a[2].split(",")) if len(a) > 2 else ())
    with open(a[1], "w") as f:
        json.dump(t, f, indent=1)
    for n, r in t["assets"].items():
        print(n, r["category"], r["collider_size"], [round(s["top_z"], 3) for s in r["surfaces"]])
    print("dropped", t["dropped"])


if __name__ == "__main__":
    main()
