"""(pod) Top-down IK success over a coarse x/z grid (WORLD-aligned axes at the base origin) at one y; the TCP is
 top-down in the WORLD when the
base link is pitched forward by `lean` (orientation in the base frame = Ry(-lean) Rz(yaw)).
usage: ik_sweep.py <profile> <arm> <y> [yaw] [lean]"""
import math
import sys

import numpy as np
import torch

from harvest.l9 import curobo9 as C
from curobo.types import GoalToolPose, Pose

profile, arm, y = sys.argv[1], sys.argv[2], float(sys.argv[3])
YAW = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
LEAN = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
w1, y1 = math.cos(-LEAN / 2), math.sin(-LEAN / 2)
w2, z2 = math.cos(YAW / 2), math.sin(YAW / 2)
q = [w1 * w2, y1 * z2, y1 * w2, w1 * z2]  # qy(-lean) * qz(yaw): top-down in the world when the base is leaned
xs, zs = np.arange(0.1, 0.81, 0.1), np.arange(-0.6, 0.41, 0.1)
PW = np.array([[x, y, z] for z in zs for x in xs], np.float32)  # world-aligned axes at the base origin
cl, sl = math.cos(LEAN), math.sin(LEAN)
P = np.stack([PW[:, 0] * cl - PW[:, 2] * sl, PW[:, 1], PW[:, 0] * sl + PW[:, 2] * cl], 1).astype(np.float32)  # Ry(-lean)
ik = C.make_ik(profile, arm, num_seeds=32, max_batch_size=len(P))
tf = C.tool_frame(profile, arm)
Q = np.tile(np.array([q], np.float32), (len(P), 1))
r = ik.solve_pose(GoalToolPose.from_poses({tf: Pose(position=torch.tensor(P, device="cuda"),
                                                      quaternion=torch.tensor(Q, device="cuda"))}, num_goalset=1))
ok = r.success.view(-1).cpu().numpy().reshape(len(zs), len(xs))
print("x:", " ".join(f"{x:4.1f}" for x in xs))
for i, z in enumerate(zs[::-1]):
    print(f"z {z:+.1f}", "  ".join("#" if v else "." for v in ok[::-1][i]))
