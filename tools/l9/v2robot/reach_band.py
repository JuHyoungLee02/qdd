"""(pod, cuRobo pylib, plain Isaac python) R1 Pro top-down reach band at the fixed torso lean (L9v2-R1, 10-03).

Grid of TCP offsets from torso_link4's origin in WORLD-aligned axes (dx ahead, dy left, dz up; the leaned base frame
is world rotated by Ry(lean)), right arm (left = y mirrored). A cell is ok when a top-down TCP (yaw 0/45/90/135 deg
about the vertical) has a self-collision-free IK solution (no world) with every arm joint >= MARGIN inside its
limits. scene placement (harvest/l9/r1_band.py) asks for the grasp height AND a carry height above a node point.
usage: reach_band.py <out.json> [lean]"""
import json
import math
import os
import sys

sys.path.insert(0, "/data/harvest/l9v2/pylib")
import numpy as np  # noqa: E402
import torch  # noqa: E402

from harvest.l9 import curobo9 as C  # noqa: E402
from curobo.types import GoalToolPose, Pose  # noqa: E402

MARGIN = 0.05
DX = (0.15, 0.85, 0.025)
DY = (-0.65, 0.35, 0.025)
DZ = (-0.60, 0.10, 0.025)
YAWS = (0, 45, 90, 135)


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]


def axis(lo, hi, st):
    return np.round(np.arange(lo, hi + 1e-9, st), 4)


def main():
    out = sys.argv[1]
    lean = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
    B = 256
    ik = C.make_ik("r1pro", "right", num_seeds=24, max_batch_size=B, self_collision_check=True)
    tf = C.tool_frame("r1pro", "right")
    lo, hi = (v.cpu().numpy()[:7] for v in ik.kinematics.get_joint_limits().position)
    xs, ys, zs = axis(*DX), axis(*DY), axis(*DZ)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    c, s = math.cos(lean), math.sin(lean)
    Pb = np.stack([c * P[:, 0] - s * P[:, 2], P[:, 1], s * P[:, 0] + c * P[:, 2]], 1)
    ok = np.zeros(len(P), bool)
    qlean = [math.cos(-lean / 2), 0, math.sin(-lean / 2), 0]
    for yaw in YAWS:
        q = qmul(qlean, [math.cos(math.radians(yaw) / 2), 0, 0, math.sin(math.radians(yaw) / 2)])
        idx = np.flatnonzero(~ok)
        for s0 in range(0, len(idx), B):
            ii = idx[s0:s0 + B]
            m = len(ii)
            pos = np.concatenate([Pb[ii], np.repeat(Pb[ii[-1:]], B - m, 0)]) if m < B else Pb[ii]
            g = GoalToolPose.from_poses({tf: Pose(position=torch.tensor(pos, device="cuda", dtype=torch.float32),
                                                  quaternion=torch.tensor([q] * B, device="cuda", dtype=torch.float32))},
                                        num_goalset=1)
            r = ik.solve_pose(g)
            sk = r.success.reshape(B, -1)[:m, 0].cpu().numpy().astype(bool)
            sol = r.js_solution.position.reshape(B, -1)[:m, :7].cpu().numpy()
            mg = np.minimum(sol - lo, hi - sol).min(1)
            ok[ii] = sk & (mg >= MARGIN)
        print("yaw", yaw, "ok", int(ok.sum()), "/", len(ok), flush=True)
    json.dump({"lean": lean, "margin": MARGIN, "yaws_deg": YAWS, "arm": "right", "frame": "torso_link4 origin, world axes",
               "x": [float(v) for v in DX], "y": [float(v) for v in DY], "z": [float(v) for v in DZ],
               "shape": [len(xs), len(ys), len(zs)], "ok": "".join("1" if v else "0" for v in ok)}, open(out, "w"))
    os._exit(0)


if __name__ == "__main__":
    main()
