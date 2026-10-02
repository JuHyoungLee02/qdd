"""(pod, cuRobo, outside the Isaac app) Ready arm pose per (profile, arm): IK (self-collision on) to a top-down TCP
(yaw `yaw` about the world vertical) when the base link is pitched forward by `lean` (R1 Pro torso lean), i.e. TCP
orientation in the base frame = Ry(-lean) Rz(yaw). usage: ready_pose.py <profile> <out.json> x y z [yaw] [lean]
[arm...]  (x y z = right-arm TCP in the cuRobo base frame; left = y mirrored, yaw negated). Prints the solutions."""
import json
import math
import os
import sys

sys.path.insert(0, "/data/harvest/l9v2/pylib")  # cuRobo 0.8 / warp 1.14 (plan9_server.PYLIB); this tool imports
# curobo directly in the collection process's own python, which plan9_server's separate-process split avoids

import torch

from harvest.l9 import curobo9 as C
from curobo.types import GoalToolPose, Pose


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]


if "READY_SEED0" in os.environ:  # DIAG 9: cuRobo's IK draws the same seeds every process by default (reruns of the
    # exact V2_READY target failed identically 3x) -- a different torch seed can find what index 0 missed
    torch.manual_seed(int(os.environ["READY_SEED0"]))

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
    # L9v2-DIAG 9: the exact target has a whole family of IK solutions (redundant 7-dof arm); the single solution
    # cuRobo hands back by default can sit right at a joint limit (pilotR V2_READY right joint2 margin 0.033 rad,
    # inside cuRobo's own 0.03 rad position_limit_clip -> effectively AT the planning limit: most carry/lift/retreat
    # moves that need that joint to grow at all then have no collision-free path). return_seeds asks for several
    # solution branches of the SAME exact pose (err_mm 0.00 for all of them in a 16-seed test, margins 0.003-0.126)
    # instead of only the one cuRobo would otherwise pick; keep the one with the largest margin to either limit.
    RS = int(os.environ.get("READY_RETURN_SEEDS", 32))
    ik = C.make_ik(profile, arm, num_seeds=int(os.environ.get("READY_SEEDS", 64)), max_batch_size=1,
                    self_collision_check=os.environ.get("SELFCOL", "1") == "1")
    tf = C.tool_frame(profile, arm)
    goal = GoalToolPose.from_poses({tf: Pose(position=torch.tensor([t], device="cuda", dtype=torch.float32),
                                              quaternion=torch.tensor([q], device="cuda", dtype=torch.float32))},
                                   num_goalset=1)
    r = ik.solve_pose(goal, return_seeds=RS)
    okv = r.success.view(-1).tolist()
    names = list(r.js_solution.joint_names)
    P = r.js_solution.position.view(len(okv), -1)
    lo, hi = (v.cpu().numpy() for v in ik.kinematics.get_joint_limits().position)
    idxs = [names.index(j) for j in C.arm_joints(profile, arm)]
    best_k, best_margin = (okv.index(True) if True in okv else 0), -1.0
    for k in range(len(okv)):
        if not okv[k]:
            continue
        qk = P[k].cpu().numpy()
        margin = float(min(min(qk[i] - lo[i], hi[i] - qk[i]) for i in idxs))
        if margin > best_margin:
            best_k, best_margin = k, margin
    k = best_k
    sol = P[k].tolist()
    arm_q = {j: round(sol[names.index(j)], 5) for j in C.arm_joints(profile, arm)}
    res[arm] = {"ok": bool(okv[k]), "n_ok": int(sum(okv)), "pos_err_mm": round(float(r.position_error.view(-1)[k]) * 1e3, 3),
                "limit_margin_rad": round(best_margin, 4), "target_base": t,
                "quat_base": [round(v, 6) for v in q], "yaw": yaw, "lean": LEAN,
                "base_link": C.base_link(profile, arm), "tool_frame": tf, "q": arm_q}
    print(profile, arm, res[arm])
json.dump(res, open(out, "w"), indent=1)
