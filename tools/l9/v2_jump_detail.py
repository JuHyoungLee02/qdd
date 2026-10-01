"""Print measured arm joints and joint targets around the largest step of one episode (L9 v2 diagnosis).
usage: python tools/l9/v2_jump_detail.py <episode dir> [window]"""
import os
import sys

import numpy as np

d = sys.argv[1]
win = int(sys.argv[2]) if len(sys.argv) > 2 else 6
z = np.load(os.path.join(d, "joints.npz"))
ids = z["arm_ids"]
q = z["q"][:, ids]
tt = z["arm_target_torque_vel"]  # [target 7, applied torque 7, computed torque 7, vel 7]
tgt = tt[:, :7]
dq = np.abs(np.diff(q, axis=0)).max(1)
dt_ = np.abs(np.diff(tgt, axis=0)).max(1)
k = int(np.argmax(dq))
np.set_printoptions(precision=3, suppress=True, linewidth=200)
print("dt", float(z["dt"]), "largest measured step", k, round(float(dq[k]), 4))
for i in range(max(0, k - win), min(len(q) - 1, k + win)):
    print(i, "dq", round(float(dq[i]), 3), "dtarget", round(float(dt_[i]), 3), "q", q[i], "tgt", tgt[i])
