"""L9 v2 diagnosis: do measured arm-joint jumps coincide with fast gripper motion? (pure numpy)
usage: python tools/l9/diag/jump_vs_grip.py <collect root> [--since EPOCH] [--thr 0.04]
For every v2 episode whose largest measured arm joint step exceeds thr: the joint, the step, the commanded step there,
whether that arm joint's applied torque sat at its effort cap, and the largest gripper-joint step within +-4 steps."""
import glob
import json
import os
import sys
from collections import Counter

import numpy as np


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    thr = float(a[a.index("--thr") + 1]) if "--thr" in a else 0.04
    c = Counter()
    for m in glob.glob(os.path.join(a[0], "**", "meta.json"), recursive=True):
        if os.path.getmtime(m) < since:
            continue
        meta = json.load(open(m))
        if meta.get("grasp_v2") is None or (meta.get("max_dq_rad") or 0) <= thr:
            continue
        ep = os.path.dirname(m)
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
        dq = np.abs(np.diff(q[:, ids], axis=0))
        s, j = np.unravel_index(int(np.argmax(dq)), dq.shape)
        cmd = abs(float(t[s + 1, j] - t[s, j])) if len(t) > s + 1 else None
        sat = bool(eff.size and abs(t[s + 1, n7 + j]) >= 0.99 * eff[2, j]) if len(t) > s + 1 else None
        lo, hi = max(0, s - 4), min(len(q) - 1, s + 4)
        gstep = float(np.abs(np.diff(q[lo:hi + 1, g], axis=0)).max()) if g and hi > lo else 0.0
        fast = gstep > 0.15
        c[(names[ids[j]][-6:], "grip_fast" if fast else "grip_still", "sat" if sat else "nosat", bool(meta.get("success")))] += 1
        print(f"{os.path.relpath(ep, a[0])[:58]:58s} ok={meta.get('success')} max {dq.max():.3f} {names[ids[j]]} step {s} "
              f"cmd {cmd if cmd is None else round(cmd, 3)} sat {sat} grip step +-4: {gstep:.2f}")
    print()
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print(k, v)


if __name__ == "__main__":
    main()
