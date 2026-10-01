"""(pod, cuRobo, outside the Isaac app) Ready arm pose per (profile, arm): IK (self-collision on) to a top-down TCP at
yaw 0 (TCP frame = base frame, identity quaternion) above the work surface, in front of the arm.
usage: ready_pose.py <profile> <out.json> x y z [arm...]   (x y z = right-arm TCP in the cuRobo base frame; left = y
mirrored). Prints the solution and its position error."""
import json
import sys

import torch

from harvest.l9 import curobo9 as C
from curobo.types import GoalToolPose, Pose

profile, out = sys.argv[1], sys.argv[2]
p = [float(v) for v in sys.argv[3:6]]
arms = sys.argv[6:] or list(C.PROFILES[profile][1])
res = {}
for arm in arms:
    t = list(p)
    if arm == "left":
        t[1] = -t[1]
    ik = C.make_ik(profile, arm, num_seeds=64)
    tf = C.tool_frame(profile, arm)
    r = ik.solve_pose(GoalToolPose.from_poses({tf: Pose(position=torch.tensor([t], device="cuda", dtype=torch.float32),
                                                          quaternion=torch.tensor([[1.0, 0, 0, 0]], device="cuda"))},
                                              num_goalset=1))
    names = list(r.js_solution.joint_names)
    q = r.js_solution.position.view(-1).tolist()
    arm_q = {j: round(q[names.index(j)], 5) for j in C.arm_joints(profile, arm)}
    res[arm] = {"ok": bool(r.success.view(-1)[0]), "pos_err_mm": round(float(r.position_error.view(-1)[0]) * 1e3, 3),
                "target_base": t, "base_link": C.base_link(profile, arm), "tool_frame": tf, "q": arm_q}
    print(profile, arm, res[arm])
json.dump(res, open(out, "w"), indent=1)
