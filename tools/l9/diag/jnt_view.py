"""L9 v2 diagnosis: per-step arm joint log of an episode (joints.npz): measured q, commanded target (incl. gravity
offset), applied / computed torque and velocity of one arm joint, plus all gripper / finger joints (pure numpy).
usage: python tools/l9/diag/jnt_view.py <episode dir> <arm joint index 0-6> [--from S] [--to S]"""
import os
import sys

import numpy as np


def main():
    ep, j = sys.argv[1], int(sys.argv[2])
    a = sys.argv[3:]
    lo = int(a[a.index("--from") + 1]) if "--from" in a else 0
    hi = int(a[a.index("--to") + 1]) if "--to" in a else 10 ** 9
    d = np.load(os.path.join(ep, "joints.npz"), allow_pickle=True)
    q = d["q" if "q" in d.files else "Q"]
    names = [str(n) for n in d["names"]]
    ids = [int(i) for i in d["arm_ids"]]
    t = d["arm_target_torque_vel"]
    eff = d["arm_kd_effort"]
    n7 = len(ids)
    fing = [i for i, n in enumerate(names) if any(s in n for s in ("finger", "gripper", "gear", "r1", "l1", "r2", "l2"))
            and i not in ids]
    print("joint", names[ids[j]], "kp/kd/effort", eff[:, j].tolist() if eff.size else None,
          "fingers", [names[i] for i in fing][:6])
    for s in range(max(lo, 0), min(hi, len(q) - 1) + 1):
        dq = q[s, ids[j]] - q[s - 1, ids[j]] if s else 0.0
        tgt, tau, ctau, vel = t[s, j], t[s, n7 + j], t[s, 2 * n7 + j], t[s, 3 * n7 + j]
        f = " ".join(f"{q[s, i]:+.3f}" for i in fing[:4])
        print(f"{s:4d} q {q[s, ids[j]]:+.4f} dq {dq:+.4f} tgt {tgt:+.4f} tau {tau:+7.2f} ctau {ctau:+8.2f} vel {vel:+.3f} | fingers {f}")


if __name__ == "__main__":
    main()
