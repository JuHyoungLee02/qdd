"""The b4 asset list for L8-D (user-log 173 / 175 / 181): gate-passed furniture pieces, display fixtures with their
passing surfaces, stable products and stack bases, pickable real objects (the L8-D object gate), material library
counts. usage: python tools/l8x_assets/b4_list.py PIECES.json DISP_PH.json DISP_THOR.json STACK.json
OLD_TALLY.json NEW_TALLY.json OUT.json"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import materials as M  # noqa: E402

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "harvest", "sim", "assets_x")


def main(argv=None):
    a = argv or sys.argv[1:]
    pieces = json.load(open(a[0]))
    disp = {**json.load(open(a[1]))["fixtures"], **json.load(open(a[2]))["fixtures"]}
    stack = json.load(open(a[3]))["stack"]
    old, new = json.load(open(a[4]))["objects"], json.load(open(a[5]))["objects"]
    objs = json.load(open(os.path.join(D, "objects_real.json")))["objects"]
    prods = json.load(open(os.path.join(D, "products.json")))["objects"]
    cat = M.usable(json.load(open(os.path.join(D, "materials.json")))["materials"])
    fam = {n: pieces["pieces"][n]["family"] for n in pieces["pass"]}
    pick = {k: objs[k]["split"] for k, d in {**old, **new}.items() if d["pass"]}
    out = {
        "furniture_pieces": {"rule": pieces["rule"], "pass": pieces["pass"], "families": sorted(set(fam.values())),
                             "table": "harvest/sim/assets_x/assets_table.json (THOR, CC BY 4.0)"},
        "display_fixtures": {"rule": "gate_display.py: products settle on each support surface; a surface passes "
                                     "with >= 75 % stable; listed = the passing surface ids",
                             "fixtures": {n: r["ok_surfaces"] for n, r in sorted(disp.items()) if r["display_ok"]},
                             "tables": ["harvest/sim/assets_x/assets_ph.json (Poly Haven, CC0, tag ph)",
                                        "harvest/sim/assets_x/assets_table.json (THOR pieces above)"]},
        "products": {"table": "harvest/sim/assets_x/products.json",
                     "stable": sorted(k for k, o in prods.items() if o.get("stable")),
                     "stack_base_ok": sorted(k for k, r in stack.items() if r.get("stack_base_ok"))},
        "pickable_objects": {"rule": "L8-D object gate (ov_tray, 35070-35072, >= 2 of 3 clean truth)",
                             "train": sorted(k for k, s in pick.items() if s == "train"),
                             "ood_o": sorted(k for k, s in pick.items() if s != "train"),
                             "table": "harvest/sim/assets_x/objects_real.json (gso_ / thor_ / gsor_ = rescaled)"},
        "materials": {"module": "harvest/sim/assets_x/materials.py", "catalog": "/data/harvest/assets_x/materials",
                      "usable": {r: sum(1 for x in cat.values() if x["role"] == r) for r in M.ROLES}},
        "licences": "docs/stage3/l8x_b4_licenses.json"}
    json.dump(out, open(a[6], "w", newline="\n"), indent=1)
    print({"pieces": len(out["furniture_pieces"]["pass"]), "families": len(out["furniture_pieces"]["families"]),
           "fixtures": len(out["display_fixtures"]["fixtures"]), "products": len(out["products"]["stable"]),
           "stack": len(out["products"]["stack_base_ok"]), "pick_train": len(out["pickable_objects"]["train"]),
           "pick_ood": len(out["pickable_objects"]["ood_o"])})


if __name__ == "__main__":
    main()
