"""(pod) harvest.l9.curobo9.make_ik smoke: a top-down and an oblique TCP target per (profile, arm), self-collision on,
plus a lock_overrides solver (fingers at another value). usage: run.sh t9 .../test_curobo9_pod.py <profile> [arm...]"""
import math
import sys

import numpy as np
import torch

from harvest.l9 import curobo9 as C
from curobo.types import GoalToolPose, Pose


def quat_from_R(R):
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    return [w, x, y, z]


def tcp_R(approach, closing_hint=(0, 1, 0)):
    a = np.asarray(approach, float)
    a /= np.linalg.norm(a)
    z = -a
    y = np.asarray(closing_hint, float)
    y = y - z * (y @ z)
    y /= np.linalg.norm(y)
    return np.column_stack([np.cross(y, z), y, z])


profile = sys.argv[1]
arms = sys.argv[2:] or list(C.PROFILES[profile][1])
TARGETS = {"ffw_sg2": (0.42, -0.22, -0.36), "franka_mast": (0.45, 0.0, 0.15), "r1pro": (0.45, -0.20, -0.25),
           "g1": (0.35, -0.20, -0.05)}
for arm in arms:
    p = np.array(TARGETS[profile], float)
    if arm == "left":
        p[1] = -p[1]
    ik = C.make_ik(profile, arm, num_seeds=32, max_batch_size=2)
    tf = C.tool_frame(profile, arm)
    th = math.radians(45)
    Rs = [tcp_R((0, 0, -1)), tcp_R((math.sin(th), 0, -math.cos(th)))]
    pos = torch.tensor([p, p], device="cuda", dtype=torch.float32)
    quat = torch.tensor([quat_from_R(R) for R in Rs], device="cuda", dtype=torch.float32)
    res = ik.solve_pose(GoalToolPose.from_poses({tf: Pose(position=pos, quaternion=quat)}, num_goalset=1))
    print(profile, arm, "base", C.base_link(profile, arm), "tool", tf, "joints", C.arm_joints(profile, arm))
    print("  top/oblique success", res.success.view(-1).tolist(), "pos err mm",
          [round(float(v) * 1e3, 2) for v in res.position_error.view(-1)])
    print("  q", [[round(float(v), 3) for v in r] for r in res.js_solution.position.view(2, -1)])
    lk = C.lock_joints(profile, arm)
    fj = [j for j in lk if "finger" in j or "gripper" in j or "hand" in j][:1]
    if fj:
        ik2 = C.make_ik(profile, arm, lock_overrides={fj[0]: (lk[fj[0]] * 0.5) or 0.4})
        r2 = ik2.solve_pose(GoalToolPose.from_poses({tf: Pose(position=pos[:1], quaternion=quat[:1])}, num_goalset=1))
        print("  lock_overrides", fj[0], "->", (lk[fj[0]] * 0.5) or 0.4, "top success", bool(r2.success.view(-1)[0]))
