"""boost2: pick DAgger scenes from the L8D b1 bundle - per world directory (variant_tz...), the first N single-step,
non-furniture episodes by seed. Prints '<dir> <ep> <ep> ...' per directory.
usage: python dagger_pick.py <bundle json> <N>"""
import json
import os
import sys
from collections import defaultdict

from harvest.sim.tasks import X_STEPS

b = json.load(open(sys.argv[1]))
n = int(sys.argv[2])
groups = defaultdict(list)
for rel in b["episodes"]:
    d = os.path.join(b["root"], rel)
    s = json.load(open(os.path.join(d, "scene.json")))
    if s["task"] in X_STEPS or s.get("furniture"):
        continue
    groups[rel.split("/")[0]].append((int(s["seed"]), d))
for g in sorted(groups):
    eps = [d for _, d in sorted(groups[g])[:n]]
    print(g, " ".join(eps))
