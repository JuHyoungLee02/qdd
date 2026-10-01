"""(pod) Validity of one arm configuration for a (profile, arm) config: self-collision link pairs (with the config's
ignore list; sphere penetration depth) and joint values against the config limits (with / without the margin).
Then plan_pose-like check: IK to the TCP 10 cm above, and cuRobo's own start-state validity via the IK solver's
self-collision cost. usage: check_q.py <profile> <arm> q1 ... q7"""
import copy
import sys

import torch

from harvest.l9 import curobo9 as C

sys.path.insert(0, "/data/harvest/l9v2robot/code/tools/l9/v2robot")
from build_curobo9 import touching_pairs  # noqa: E402

profile, arm = sys.argv[1], sys.argv[2]
q = [float(v) for v in sys.argv[3:10]]
cfg = C.load_config(profile, arm)
kd = cfg["robot_cfg"]["kinematics"]
names = C.arm_joints(profile, arm)
qn = dict(zip(names, q))
ign = kd["self_collision_ignore"]
pairs = touching_pairs(kd, qn)
real = [p for p in pairs if p[1] not in ign.get(p[0], []) and p[0] not in ign.get(p[1], [])]
print("touching pairs (all):", len(pairs), "not ignored:", real)
from curobo._src.robot.kinematics.kinematics import Kinematics  # noqa: E402
from curobo._src.robot.kinematics.kinematics_cfg import KinematicsCfg  # noqa: E402
kc = KinematicsCfg.from_data_dict(copy.deepcopy(kd))
kin = Kinematics(kc)
lim = kin.get_joint_limits().position.cpu()
for i, j in enumerate(kin.joint_names):
    lo, hi = float(lim[0, i]), float(lim[1, i])
    flag = "OUT" if not lo <= qn[j] <= hi else ""
    print(f"  {j:16s} q {qn[j]:+.4f}  cfg limits [{lo:+.4f}, {hi:+.4f}] {flag}")
