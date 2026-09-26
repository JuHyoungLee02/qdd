"""Collider boxes of mesh furniture (pod, pxr) -> JSON {name: [[cx, cy, cz, hx, hy, hz, r00..r22], ...]} in the
piece's normalised frame (collider bbox bottom-centre at the origin, = assets table origin_offset), so a spawn check
can test robot bodies against the real collision geometry instead of the piece's bbox (the bbox of a desk with a
tall back part covers the space above its top: Desk_301_1 / Dresser_219_1 false positives, v4/v7).
Mesh colliders are taken as their local box.
usage: python tools/l8x_assets/collider_boxes.py TABLE.json [TABLE2.json ...] --out OUT.json"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x.usd_import import collider_boxes  # noqa: E402


def boxes_of(usd: str, origin) -> list:
    from pxr import Usd
    out = []
    for _, C in collider_boxes(Usd.Stage.Open(usd)):
        C = np.asarray(C, float) - np.asarray(origin, float)  # 8 corners, (x, y, z) nested lo/hi order
        c = C.mean(0)
        ax = [C[4] - C[0], C[2] - C[0], C[1] - C[0]]  # local x, y, z edges
        h = [float(np.linalg.norm(v)) / 2 for v in ax]
        R = np.stack([v / max(np.linalg.norm(v), 1e-12) for v in ax], 1)  # columns = local axes in piece frame
        out.append([round(float(v), 5) for v in (*c, *h, *R.ravel())])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("tables", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = {}
    for t in a.tables:
        for name, r in json.load(open(t))["assets"].items():
            res[name] = boxes_of(r["dst"], r["origin_offset"])  # spawn: base_pos - R(yaw) origin_offset
    with open(a.out, "w") as f:
        json.dump(res, f)
    print(len(res), "pieces,", sum(len(v) for v in res.values()), "boxes ->", a.out)


if __name__ == "__main__":
    main()
