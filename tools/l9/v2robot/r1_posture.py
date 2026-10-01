"""(pure) R1 Pro torso posture study: for a torso pose (hip forward p1, link2 pitch p2, lean l) give the torso_link4
pose, the arm-base height and the head ZED view of work points (pixel of points on the surface in a 672x376 render
with the GalaxeaManipSim 100.8 deg horizontal FOV). usage: python tools/l9/v2robot/r1_posture.py <urdf> [surface]"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from urdf_fk import Urdf  # noqa: E402

W, H, HFOV = 672, 376, 100.837


def torso_q(p1, p2, lean):
    return {"torso_joint1": p1, "torso_joint2": p2 - p1, "torso_joint3": p2 - lean, "torso_joint4": 0.0}


def view(u, q, root_x, pts):
    T = u.T_root("zed_link", q)
    T[0, 3] += root_x
    # SAPIEN mount quat [1, 1, -1, 1] / 2 on zed_link: camera x forward, y left, z up
    w, x, y, z = 0.5, 0.5, -0.5, 0.5
    Rm = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                   [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                   [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    R = T[:3, :3] @ Rm
    f = (W / 2) / math.tan(math.radians(HFOV) / 2)
    out = []
    for p in pts:
        d = R.T @ (np.asarray(p) - T[:3, 3])
        out.append((round(W / 2 - f * d[1] / d[0]), round(H / 2 - f * d[2] / d[0])) if d[0] > 0 else None)
    pitch = math.degrees(math.asin(-R[2, 0]))
    return T[:3, 3], pitch, out


def main():
    u = Urdf(sys.argv[1])
    surf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.75
    root_x = -0.05
    pts = [(x, y, surf) for x in (0.40, 0.50, 0.60) for y in (-0.2, 0.2)]
    for lean in (0.4, 0.6, 0.8):
        for p1 in (0.0, 0.3, 0.5):
            for p2 in (0.0, -0.3, -0.6):
                q = torso_q(p1, p2, lean)
                t4 = u.T_root("torso_link4", q)[:3, 3] + [root_x, 0, 0]
                sh = u.T_root("right_arm_base_link", q)[:3, 3] + [root_x, 0, 0]
                cam, pitch, px = view(u, q, root_x, pts)
                print(f"lean {lean:.1f} p1 {p1:.1f} p2 {p2:+.1f}  torso4 x {t4[0]:+.2f} z {t4[2]:.2f}  shoulder x "
                      f"{sh[0]:+.2f} above {sh[2] - surf:+.2f}  cam x {cam[0]:+.2f} h {cam[2] - surf:.2f} pitch "
                      f"{pitch:.0f}  px {px}")


if __name__ == "__main__":
    main()
