"""L9 v2 diagnosis: gripper slams and wrist saturation per episode (joints.npz; pure numpy).
usage: python tools/l9/diag/grip_slam.py <episode dir> [...]
Prints: largest gripper-joint step (rad / control step), number of steps with any gripper joint step > 0.3 rad, steps
where an arm joint's applied torque sat at its effort cap, the largest measured arm joint step and its joint."""
import os
import sys

import numpy as np


def main():
    for ep in sys.argv[1:]:
        p = os.path.join(ep, "joints.npz")
        if not os.path.exists(p):
            continue
        d = np.load(p, allow_pickle=True)
        q = d["q" if "q" in d.files else "Q"]
        names = [str(n) for n in d["names"]]
        ids = [int(i) for i in d["arm_ids"]]
        t, eff = d["arm_target_torque_vel"], d["arm_kd_effort"]
        n7 = len(ids)
        g = [i for i, n in enumerate(names) if "gripper" in n or "finger" in n]
        gs = np.abs(np.diff(q[:, g], axis=0)).max(1) if g else np.zeros(len(q) - 1)
        sat = (np.abs(t[:, n7:2 * n7]) >= 0.99 * eff[2][None]).any(1) if eff.size else np.zeros(len(t), bool)
        dq = np.abs(np.diff(q[:, ids], axis=0))
        s, j = np.unravel_index(int(np.argmax(dq)), dq.shape)
        print(f"{ep.rstrip('/').rsplit('/', 2)[-2:]} grip max step {gs.max():.2f} rad, steps > 0.3: {int((gs > 0.3).sum())}, "
              f"arm torque-sat steps {int(sat.sum())}, max arm step {dq.max():.4f} ({names[ids[j]]} @ {s})")


if __name__ == "__main__":
    main()
