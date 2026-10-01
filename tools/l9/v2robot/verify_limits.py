"""(pod) cuRobo IK solutions vs the sim joint limits: 200 random TCP targets in the workspace in front of the arm
(random position in a box, approach drawn from top / oblique / horizontal), batched IK with self-collision, then
count solved arm joint values outside [lower, upper] (sim = USD limits json if given, else the URDF) and outside
the margin band. usage: verify_limits.py <profile> <arm> <box x0 x1 y0 y1 z0 z1> [usd_limits.json]"""
import json
import math
import sys

import numpy as np
import torch

from harvest.l9 import curobo9 as C
from curobo.types import GoalToolPose, Pose

sys.path.insert(0, "/data/harvest/l9v2robot/code/tools/l9/v2robot")
from urdf_fk import Urdf  # noqa: E402


def quat(R):
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    return [w, x, y, z]


profile, arm = sys.argv[1], sys.argv[2]
box = [float(v) for v in sys.argv[3:9]]
usd = json.load(open(sys.argv[9])) if len(sys.argv) > 9 else None
n = 200
rng = np.random.default_rng(5)
pos, qs = [], []
for i in range(n):
    p = [rng.uniform(box[0], box[1]), rng.uniform(box[2], box[3]), rng.uniform(box[4], box[5])]
    th = math.radians([0, 15, 40, 55, 80][i % 5])
    az = rng.uniform(-math.pi, math.pi)
    a = np.array([math.sin(th) * math.cos(az), math.sin(th) * math.sin(az), -math.cos(th)])
    z = -a
    y = np.cross(z, [0.0, 0.0, 1.0]) if abs(z[2]) < 0.99 else np.array([0.0, 1.0, 0.0])
    y /= np.linalg.norm(y)
    roll = rng.uniform(-math.pi, math.pi)
    y = y * math.cos(roll) + np.cross(z, y) * math.sin(roll)
    R = np.column_stack([np.cross(y, z), y, z])
    pos.append(p)
    qs.append(quat(R))
ik = C.make_ik(profile, arm, num_seeds=32, max_batch_size=n)
tf = C.tool_frame(profile, arm)
res = ik.solve_pose(GoalToolPose.from_poses({tf: Pose(
    position=torch.tensor(np.array(pos), device="cuda", dtype=torch.float32),
    quaternion=torch.tensor(np.array(qs), device="cuda", dtype=torch.float32))}, num_goalset=1))
ok = res.success.view(-1).cpu().numpy()
names = list(res.js_solution.joint_names)
Q = res.js_solution.position.view(n, -1).cpu().numpy()
u = Urdf(C.load_config(profile, arm)["robot_cfg"]["kinematics"]["urdf_path"])
worst = 0.0
out_lim = out_margin = 0
for j in C.arm_joints(profile, arm):
    lo, hi = (usd[j]["lower"], usd[j]["upper"]) if usd and j in usd else (u.joints[j]["lower"], u.joints[j]["upper"])
    v = Q[ok, names.index(j)]
    over = np.maximum(lo - v, v - hi)
    worst = max(worst, float(over.max()) if len(v) else 0.0)
    out_lim += int((over > 1e-6).sum())
    out_margin += int((over > -0.03 + 1e-4).sum())
print(f"{profile} {arm}: solved {int(ok.sum())}/{n}; arm values outside sim limits {out_lim}, inside-margin violations "
      f"{out_margin}, worst excess {worst * 1e3:.2f} mrad (negative = inside)")
