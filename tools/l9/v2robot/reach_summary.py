"""Reach-map rates inside a table workspace box per profile (pure; reads assets9/reach_v2/*.json).
Boxes (right arm, cuRobo base frame; left = y mirrored) are [hypothesis] typical L9 work regions:
ffw_sg2 TCP 0.05-0.25 m above a table 0.48 m below the shoulders; franka on a stand 0-0.12 m below the surface;
r1pro torso squat (shoulders 0.50 above the surface); g1 pelvis 0.793, surface 0.65.
usage: python tools/l9/v2robot/reach_summary.py [json...]"""
import glob
import json
import os
import sys

import numpy as np

WS = {"ffw_sg2": ((0.30, 0.60), (-0.45, 0.00), (-0.45, -0.25)),
      "franka_mast": ((0.30, 0.65), (-0.25, 0.25), (0.05, 0.30)),
      "r1pro": ((0.35, 0.65), (-0.45, 0.05), (-0.15, 0.05)),
      "g1": ((0.20, 0.45), (-0.35, 0.05), (-0.15, 0.05))}
files = sys.argv[1:] or sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "..", "..", "harvest", "l9",
                                                      "assets9", "reach_v2", "*.json")))
for f in files:
    d = json.load(open(f))
    g = d["grid"]
    ax = {k: g[k]["lo"] + g[k]["step"] * np.arange(g[k]["n"]) for k in "xyz"}
    X, Y, Z = np.meshgrid(ax["x"], ax["y"], ax["z"], indexing="ij")
    (x0, x1), (y0, y1), (z0, z1) = WS[d["profile"]]
    if d["arm"] == "left":
        y0, y1 = -y1, -y0
    m = ((X >= x0 - 1e-9) & (X <= x1 + 1e-9) & (Y >= y0 - 1e-9) & (Y <= y1 + 1e-9) & (Z >= z0 - 1e-9) &
         (Z <= z1 + 1e-9)).ravel()
    out = {c: round(float(np.array([ch == "1" for ch in d["ok"][c]])[m].mean()), 3) for c in d["ok"]}
    allc = {c: d["rates"][c]["cells_reachable"] for c in d["rates"]}
    print(f"{d['profile']:12s} {d['arm']:5s} workspace cells {int(m.sum()):4d}: {out}   whole grid: {allc}")
