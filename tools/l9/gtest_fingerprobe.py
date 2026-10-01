"""L9 v2 grasp test check: geometric finger gap of the floating gripper URDF per drive q (all four finger joints = q),
in TCP-frame z bands (pad band and above), from the collision meshes, against the json width_to_joint table.
  python tools/l9/gtest_fingerprobe.py [--grip ffw_sg2_right]"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from tools.l9.v2robot.urdf_fk import Urdf  # noqa: E402

GD = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "harvest", "l9",
                  "assets9", "grippers")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grip", default="ffw_sg2_right")
    a = ap.parse_args()
    gj = json.load(open(os.path.join(GD, a.grip + ".json")))
    u = Urdf(os.path.join(GD, a.grip + ".urdf"))
    tcp = gj["tcp_link"]
    joints = list(gj["finger_joints"]["drive"]) + list(gj["finger_joints"]["followers"])
    links = [u.joints[j]["child"] for j in joints]
    tab = gj["width_to_joint"]
    bands = [(-0.03, -0.01), (-0.01, 0.01), (0.01, 0.03), (0.03, 0.06), (0.06, 0.10)]
    for kind in ("collision", "visual"):
        print(kind)
        for w, q in zip(tab["width_m"], tab["drive_q"]):
            qd = {j: q for j in joints}
            P = [u.link_points(l, tcp, qd, kind) for l in links]
            P = np.concatenate([p for p in P if len(p)])
            row = []
            for z0, z1 in bands:
                m = (P[:, 2] >= z0) & (P[:, 2] < z1) & (np.abs(P[:, 0]) < 0.02)
                pos, neg = P[m & (P[:, 1] > 0), 1], P[m & (P[:, 1] < 0), 1]
                row.append(f"{(pos.min() - neg.max()) * 100:6.2f}" if len(pos) and len(neg) else "   -  ")
            print(f"  q={q:4.2f} table w={w * 100:5.2f} cm | gap by z band {bands}: " + " ".join(row))


if __name__ == "__main__":
    main()
