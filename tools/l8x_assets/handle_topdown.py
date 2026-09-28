"""Which drawer handles can a top-down gripper take (pod, pxr)? For THOR furniture with drawer (prismatic) joints and
separate handle bodies: in the static copy's canonical frame (assets_table dst, Y-up fixed, bottom-centre origin,
then the scene yaw -90 deg so the front faces the robot, -x), per handle collider box:
  open_above   no other collider overlaps the handle's xy footprint grown by the finger margins above its top
  standoff     the gap between the handle's back (+x) and the next collider behind it (the drawer front) >= 12 mm
               (the rear finger pad goes there when the fingers close along x)
  top_z        handle top height above the floor (the grasp height; the lift brings it into the reach band)
usage: python tools/l8x_assets/handle_topdown.py assets_table.json NAME [NAME ...] --out handles.json"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x.usd_import import collider_boxes  # noqa: E402

FINGER_X = 0.02  # the pads' reach in front of / behind the handle along the closing axis
FINGER_Y = 0.015
STANDOFF_MIN = 0.012
FRONT_X, FRONT_Z = 0.03, 0.02  # change 11: the front-grasp finger sweep around the bar
YAW = -math.pi / 2


def main(argv=None):
    try:
        from pxr import Usd
    except ImportError:  # Isaac python: pxr comes with the kit app
        from isaacsim import SimulationApp
        SimulationApp({"headless": True})
        from pxr import Usd
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("names", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rows = json.load(open(a.table))["assets"]
    c, s = math.cos(YAW), math.sin(YAW)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    out = {}
    for n in a.names:
        r = rows.get(n)
        if r is None:
            out[n] = {"error": "not in the table"}
            continue
        boxes = collider_boxes(Usd.Stage.Open(r["dst"]))
        off = np.asarray(r["origin_offset"], float)
        B = [(p, (np.asarray(C, float) - off) @ R.T) for p, C in boxes]  # scene frame (front towards -x)
        ext = [(p, C.min(0), C.max(0)) for p, C in B]
        hs = []
        for p, lo, hi in ext:
            if "handle" not in p.lower():
                continue
            above = [q for q, l2, h2 in ext if q != p and l2[2] > hi[2] - 0.002 and l2[0] < hi[0] + FINGER_X
                     and h2[0] > lo[0] - FINGER_X and l2[1] < hi[1] + FINGER_Y and h2[1] > lo[1] - FINGER_Y]
            behind = [l2[0] - hi[0] for q, l2, h2 in ext if q != p and l2[0] >= hi[0] - 0.002
                      and l2[1] < hi[1] and h2[1] > lo[1] and l2[2] < hi[2] and h2[2] > lo[2]]
            standoff = min(behind) if behind else 1.0
            # change 11: front access for vertical fingers -- no other collider (drawer front of a recessed handle,
            # slot walls) in the zone the fingers sweep: 3 cm in front of the bar to its back, 2 cm above / below it,
            # the bar middle (2 cm in from its ends, clear of the mounting posts)
            body = p.rsplit("/", 1)[-1].split("_PrimitiveCollider")[0]
            blk = [q for q, l2, h2 in ext if body not in q.rsplit("/", 1)[-1] and l2[0] < hi[0] + 0.002
                   and h2[0] > lo[0] - FRONT_X and l2[1] < hi[1] - 0.02 and h2[1] > lo[1] + 0.02
                   and l2[2] < hi[2] + FRONT_Z and h2[2] > lo[2] - FRONT_Z]
            hs.append({"prim": p.rsplit("/", 1)[-1], "top_z": round(float(hi[2]), 3),
                       "centre": [round(float(v), 3) for v in (lo + hi) / 2],
                       "size": [round(float(v), 3) for v in hi - lo], "open_above": bool(not above),
                       "standoff_m": round(float(standoff), 3), "front_ok": bool(not blk),
                       "front_block": [q.rsplit("/", 1)[-1] for q in blk][:3],
                       "ok": bool((not above) and standoff >= STANDOFF_MIN)})
        out[n] = {"handles": hs, "n_ok": sum(h["ok"] for h in hs), "height": r["collider_size"][2]}
        print(n, "handles", len(hs), "top-down ok", out[n]["n_ok"],
              sorted({h["top_z"] for h in hs if h["ok"]}), flush=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
