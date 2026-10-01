"""E-LIB0c cause check (no model; user 10-02 00시 "컵 … 중심에다가 밀어넣어서 잡으려하니까 거긴아무것도 없으니"):
for every 'grasp + close' call of an arm, from that call's saved head depth (robot removed) and camera:
  resolved region (the resolver's object around the pointed pixel) -> top height, and the measured surface height in a
  1.5 cm radius around the grasp target xy (= the region top-band centre) -> centre_drop = top - centre surface.
  hollow = centre_drop >= 2 cm (25th percentile of the surface heights: the inner floor seen at the centre).
  outcome = the pad gap at the next call (scaled for Ab): empty close (< 1.0 cm), holding (>= 1.0 cm).
-> <out>/hollow_<arm>.json with per-call rows and the 2x2 (hollow x empty) table.
usage: hollow_check.py <root /data/harvest/out/lib0> <arm>"""
import glob
import json
import os
import sys

import numpy as np

from harvest.astra_motion.geometry import Cam
from harvest.astra_solo import resolve as RS

root, arm = sys.argv[1], sys.argv[2]
EMPTY_M = 0.010
rows = []
for res_p in sorted(glob.glob(os.path.join(root, arm, "*", "t*_k*", "result.json"))):
    ep = os.path.dirname(res_p)
    R = json.load(open(res_p))
    calls = R["calls"]
    for j, c in enumerate(calls):
        cm = ((c.get("parsed") or {}).get("command") or {})
        if not (cm.get("mode") == "point" and cm.get("height") == "grasp" and cm.get("gripper") == "close"):
            continue
        res = c.get("resolved") or {}
        if res.get("kind") != "object" or res.get("goal") is None:
            continue
        d = os.path.join(ep, "calls", f"c{c['call']:03d}")
        try:
            depth = np.load(os.path.join(d, "head_depth.npz"))["depth"]
            cam = Cam.from_json(json.load(open(os.path.join(d, "cams.json")))["head"])
        except OSError:
            continue
        P = RS.depth_points(cam, depth)
        g = np.asarray(res["goal"], float)
        near = np.isfinite(P).all(-1) & (np.linalg.norm(P[..., :2] - g[:2], axis=-1) < 0.015)
        if near.sum() < 5:
            continue
        surf = float(np.percentile(P[..., 2][near], 25))
        drop = float(res["top"]) - surf
        nxt = next((x for x in calls[j + 1:] if x["attempt"] == 0), None)
        gap = None if nxt is None else float(nxt["truth"]["grip_w"])
        rows.append({"ep": os.path.relpath(ep, root), "call": c["call"], "top": res["top"], "plane": res.get("plane"),
                     "centre_surface": round(surf, 4), "centre_drop_m": round(drop, 4), "n_px": res.get("n_px"),
                     "gap_after": gap, "hollow": drop >= 0.02, "empty": gap is not None and gap < EMPTY_M})
T = {f"{h}_{e}": sum(1 for r in rows if r["hollow"] == h and r["empty"] == e) for h in (True, False) for e in (True, False)}
eps = {r["ep"] for r in rows}
he = {r["ep"] for r in rows if r["hollow"] and r["empty"]}
summ = {"n_grasp_calls": len(rows), "table_hollow_empty": T,
        "empty_rate_hollow": round(T["True_True"] / max(1, T["True_True"] + T["True_False"]), 3),
        "empty_rate_solid": round(T["False_True"] / max(1, T["False_True"] + T["False_False"]), 3),
        "episodes_with_grasp": len(eps), "episodes_with_hollow_empty": len(he)}
json.dump({"summary": summ, "rows": rows}, open(os.path.join(root, f"hollow_{arm}.json"), "w"), indent=1)
print(json.dumps(summ))
