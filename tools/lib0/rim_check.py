"""E-LIB0c offline check of harvest.lib0.rim on an arm's saved 'grasp + close' calls (head depth, camera, point, TCP):
detector verdict x outcome (empty close = pad gap at the next call < 1.0 cm in the arm's units) -> <root>/rim_<arm>.json.
usage: rim_check.py <root> <arm>"""
import collections
import glob
import json
import os
import sys

import numpy as np

from harvest.astra_motion.geometry import Cam
from harvest.astra_solo import resolve as RS
from harvest.lib0.rim import region_points, rim_of

RS.robot_mask = lambda hgt, plane, tcp: np.zeros(np.shape(hgt), bool)
root, arm = sys.argv[1], sys.argv[2]
rows = []
for res_p in sorted(glob.glob(os.path.join(root, arm, "*", "t*_k*", "result.json"))):
    ep = os.path.dirname(res_p)
    R = json.load(open(res_p))
    tz = json.load(open(os.path.join(ep, "row.json"))).get("table_z")
    calls = R["calls"]
    for j, c in enumerate(calls):
        cm = ((c.get("parsed") or {}).get("command") or {})
        if not (cm.get("mode") == "point" and cm.get("height") == "grasp" and cm.get("gripper") == "close"):
            continue
        d = os.path.join(ep, "calls", f"c{c['call']:03d}")
        try:
            depth = np.load(os.path.join(d, "head_depth.npz"))["depth"]
            cam = Cam.from_json(json.load(open(os.path.join(d, "cams.json")))["head"])
        except OSError:
            continue
        P, plane, r = region_points(cam, depth, tz, cm["point_2d"], tcp=c["truth"]["tcp"])
        v = rim_of(P, c["truth"]["tcp"])
        nxt = next((x for x in calls[j + 1:] if x["attempt"] == 0), None)
        gap = None if nxt is None else float(nxt["truth"]["grip_w"])
        rows.append({"ep": os.path.relpath(ep, root), "call": c["call"], "why": v["why"], "hollow": v["hollow"],
                     "width_y": v.get("width_y"), "drop": v.get("drop"), "gap_after": gap,
                     "empty": gap is not None and gap < 0.010})
T = collections.Counter((r["hollow"], r["empty"]) for r in rows)
W = collections.Counter((r["why"], r["empty"]) for r in rows)
S = collections.Counter((r["ep"].split("/")[1], r["hollow"], r["empty"]) for r in rows)
summ = {"n": len(rows), "hollow_x_empty": {f"{k[0]}_{k[1]}": v for k, v in T.items()},
        "why_x_empty": {f"{k[0]}_{k[1]}": v for k, v in sorted(W.items())},
        "suite_hollow_empty": {f"{k[0]}_{k[1]}_{k[2]}": v for k, v in sorted(S.items())},
        "episodes_hollow": len({r["ep"] for r in rows if r["hollow"]})}
json.dump({"summary": summ, "rows": rows}, open(os.path.join(root, f"rim_{arm}.json"), "w"), indent=1)
print(json.dumps(summ, indent=0))
