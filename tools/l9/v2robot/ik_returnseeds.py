"""(pod, cuRobo) diagnosis: solve_pose with return_seeds>1 and an optional seed_config warm start, to see the spread
of IK solutions (and their joint-limit margins) for one target, instead of only the single best.
usage: ik_returnseeds.py <profile> <arm> <x> <y> <z> <yaw> <lean> [return_seeds] [seed_q0 .. seed_q6]"""
import sys

sys.path.insert(0, "/data/harvest/l9v2/pylib")

import math

import numpy as np
import torch

from harvest.l9 import curobo9 as C
from curobo.types import GoalToolPose, Pose, JointState


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]


def main():
    a = sys.argv[1:]
    profile, arm = a[0], a[1]
    x, y, z, yaw, lean = (float(v) for v in a[2:7])
    rs = int(a[7]) if len(a) > 7 else 8
    seed_q = [float(v) for v in a[8:15]] if len(a) > 14 else None
    q = qmul([math.cos(-lean / 2), 0, math.sin(-lean / 2), 0], [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)])
    ik = C.make_ik(profile, arm, num_seeds=64, max_batch_size=1)
    tf = C.tool_frame(profile, arm)
    g = GoalToolPose.from_poses({tf: Pose(position=torch.tensor([[x, y, z]], device="cuda", dtype=torch.float32),
                                           quaternion=torch.tensor([q], device="cuda", dtype=torch.float32))},
                                 num_goalset=1)
    cur = None
    if seed_q is not None:
        t = torch.tensor([seed_q], device="cuda", dtype=torch.float32)
        cur = JointState.from_position(t, joint_names=ik.joint_names)
    r = ik.solve_pose(g, seed_config=cur, return_seeds=rs)
    names = list(r.js_solution.joint_names)
    idxs = [names.index(j) for j in C.arm_joints(profile, arm)]
    lo, hi = (v.cpu().numpy() for v in ik.kinematics.get_joint_limits().position)
    ok = r.success.view(-1).cpu().numpy()
    P = r.js_solution.position.view(-1, len(names)).cpu().numpy()
    err = r.position_error.view(-1).cpu().numpy()
    print(f"n_candidates {len(ok)} n_ok {int(ok.sum())}")
    for i in range(len(ok)):
        m = min(min(P[i, j] - lo[j], hi[j] - P[i, j]) for j in idxs)
        print(f"  {i}: ok={bool(ok[i])} err_mm={err[i]*1e3:.2f} margin={m:.4f} "
              f"q={[round(float(P[i, j]), 4) for j in idxs]}")


if __name__ == "__main__":
    main()
