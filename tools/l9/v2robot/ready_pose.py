"""(pod, cuRobo, outside the Isaac app) Ready arm pose per (profile, arm): IK (self-collision on) to a top-down TCP
(yaw `yaw` about the world vertical) when the base link is pitched forward by `lean` (R1 Pro torso lean), i.e. TCP
orientation in the base frame = Ry(-lean) Rz(yaw). usage: ready_pose.py <profile> <out.json> x y z [yaw] [lean]
[arm...]  (x y z = right-arm TCP in the cuRobo base frame; left = y mirrored, yaw negated). Prints the solutions."""
import json
import math
import sys

import numpy as np
import torch

from harvest.l9 import curobo9 as C
from curobo.types import GoalToolPose, Pose


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]


profile, out = sys.argv[1], sys.argv[2]
p = [float(v) for v in sys.argv[3:6]]
YAW = float(sys.argv[6]) if len(sys.argv) > 6 else 1.5708  # AI Worker INIT: top-down yaw pi/2
LEAN = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0
arms = sys.argv[8:] or list(C.PROFILES[profile][1])
res = {}
for arm in arms:
    t = list(p)
    yaw = YAW
    if arm == "left":
        t[1], yaw = -t[1], -YAW
    q = qmul([math.cos(-LEAN / 2), 0, math.sin(-LEAN / 2), 0], [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)])
    offs = [(0.0, 0.0)] + [(dx, dz) for dx in (-0.05, 0.0, 0.05) for dz in (-0.05, 0.0, 0.05) if dx or dz]
    T = [[t[0] + dx, t[1], t[2] + dz] for dx, dz in offs]  # batch: the target + 8 neighbours (first success wins)
    ik = C.make_ik(profile, arm, num_seeds=64, max_batch_size=len(T))
    tf = C.tool_frame(profile, arm)
    r = ik.solve_pose(GoalToolPose.from_poses({tf: Pose(position=torch.tensor(T, device="cuda", dtype=torch.float32),
                                                          quaternion=torch.tensor([q] * len(T), device="cuda", dtype=torch.float32))},
                                              num_goalset=1))
    okv = r.success.view(-1).tolist()
    k = okv.index(True) if True in okv else 0
    t = T[k]
    names = list(r.js_solution.joint_names)
    sol = r.js_solution.position.view(len(T), -1)[k].tolist()
    arm_q = {j: round(sol[names.index(j)], 5) for j in C.arm_joints(profile, arm)}
    res[arm] = {"ok": bool(okv[k]), "pos_err_mm": round(float(r.position_error.view(-1)[k]) * 1e3, 3),
                "target_base": t, "quat_base": [round(v, 6) for v in q], "yaw": yaw, "lean": LEAN,
                "base_link": C.base_link(profile, arm), "tool_frame": tf, "q": arm_q}
    print(profile, arm, res[arm])
json.dump(res, open(out, "w"), indent=1)
