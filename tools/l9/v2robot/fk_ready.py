"""(pod, cuRobo) FK of a given joint vector -> TCP pose in the base frame (torso_link4), to recover the real target
of an existing V2_READY value without guessing x/y/z/yaw/lean.
usage: fk_ready.py <profile> <arm> <q0> <q1> ... <q6>"""
import sys

sys.path.insert(0, "/data/harvest/l9v2/pylib")

import numpy as np

from harvest.l9 import curobo9 as C
from harvest.l9 import plan9 as P9
from harvest.l9.grasp9 import mat_quat


def main():
    profile, arm = sys.argv[1], sys.argv[2]
    q = [float(v) for v in sys.argv[3:10]]
    pl = P9.Planner9(C.load_config(profile, arm))
    T = pl.tool_T(np.asarray(q, float))
    print("q", q)
    print("TCP pos (base frame)", np.round(T[:3, 3], 5).tolist())
    print("TCP quat wxyz (base frame)", np.round(mat_quat(T[:3, :3]), 6).tolist())
    lo, hi = pl._limits()
    names = pl.joint_names
    idxs = [names.index(j) for j in C.arm_joints(profile, arm)]
    print("margin to limits (rad)", [round(float(min(q[k] - lo[i], hi[i] - q[k])), 4)
                                      for k, i in enumerate(idxs)])


if __name__ == "__main__":
    main()
