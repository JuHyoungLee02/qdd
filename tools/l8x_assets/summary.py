"""Print / write the surface table of every parametric kind over seeds (pure; optional L8-D reach probe).
usage: python tools/l8x_assets/summary.py [--seeds 20] [--reach reach_base.json] [--out summary.json]"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import furniture as FU  # noqa: E402
from harvest.sim.assets_x.reach import ReachModel  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--reach", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--mesh-table", default=None)
    a = ap.parse_args(argv)
    rm = ReachModel.load(a.reach) if a.reach else None
    mesh = json.load(open(a.mesh_table))["assets"] if a.mesh_table else None
    rows = {}
    for kind in FU.KINDS + FU.mesh_kinds(mesh):
        per = {}
        for seed in range(a.seeds):
            sc = FU.sample_scene(kind, seed, reach=rm, mesh_assets=mesh)
            regs = {p["surface"]: p for p in sc["placement_regions"]}
            for s in sc["surfaces"]:
                d = per.setdefault(s["kind"], {"n": 0, "top": [], "usable": 0, "reasons": {}})
                d["n"] += 1
                d["top"].append(s["top_z"])
                if rm is not None:
                    p = regs[s["id"]]
                    if p["region"] is not None:
                        d["usable"] += 1
                    else:
                        d["reasons"][p["reason"]] = d["reasons"].get(p["reason"], 0) + 1
        rows[kind] = {k: {"n": v["n"], "top_min": min(v["top"]), "top_max": max(v["top"]),
                          "usable": v["usable"] if rm is not None else None, "reasons": v["reasons"]}
                      for k, v in per.items()}
        for k, v in rows[kind].items():
            print(f"{kind:16s} {k:16s} n={v['n']:3d} top {v['top_min']:.3f}-{v['top_max']:.3f} "
                  f"usable={v['usable']} {v['reasons']}")
    if a.out:
        with open(a.out, "w") as f:
            json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
