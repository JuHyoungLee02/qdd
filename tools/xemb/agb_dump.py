"""AgiBot: per kept episode, dump the proprio fields needed for point labels to npz (h5py lives in the python 3.11
env; the video / projection tools run in 3.12). Fields: state/end/position (T, 2, 3) + orientation (T, 2, 4),
state/effector/position (T, 2) gripper, state/head/position (T, 2), timestamps when present.
usage (pod, venv_train + pylib_xemb_train): python -m xemb.agb_dump KEEP_DIR [TASK ...]"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np


def main(keep, tasks):
    import h5py
    n = 0
    for h in sorted(glob.glob(os.path.join(keep, "proprio", "*", "*", "proprio_stats.h5"))):
        task, ep = h.split(os.sep)[-3:-1]
        if tasks and task not in tasks:
            continue
        out = os.path.join(keep, "npz", task, f"{ep}.npz")
        if os.path.exists(out):
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with h5py.File(h, "r") as f:
            d = {"end_pos": f["state/end/position"][()], "end_quat": f["state/end/orientation"][()],
                 "grip": f["state/effector/position"][()], "head": f["state/head/position"][()]}
            if "timestamp" in f:
                d["ts"] = f["timestamp"][()]
        np.savez_compressed(out, **d)
        n += 1
    print("dumped", n)


if __name__ == "__main__":
    main(sys.argv[1], set(sys.argv[2:]))
