"""Pick E-DIST8 closed-loop episodes from an L8D collect set: for each given variant_tz directory, the first N
single-step, non-furniture episodes (sorted by seed). Prints one line per world group: '<dir> <ep> <ep> ...'.
usage: python dist8_pick.py <collect set dir> <N> <vdir> [<vdir> ...]"""
import glob
import json
import os
import sys

from harvest.sim.tasks import X_STEPS

root, n, vdirs = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
for v in vdirs:
    eps = []
    for d in sorted(glob.glob(os.path.join(root, v, "*_s*")), key=lambda p: int(p.rsplit("_s", 1)[1])):
        s = json.load(open(os.path.join(d, "scene.json")))
        if s["task"] in X_STEPS or s.get("furniture"):
            continue
        eps.append(d)
        if len(eps) == n:
            break
    print(v, " ".join(eps))
