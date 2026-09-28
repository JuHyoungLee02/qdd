"""user-log 171 episode picks. mode 'map': OOD-H drx_tz0.980 first 4 + drx_tz0.740 first 2 (by seed); mode 'c30 <set>':
30 single-step non-furniture episodes of an L8-X evaluation set (collect/<set>), evenly spaced over the seed-sorted
list. Prints '<episode dirs>' per world directory (one line per world config).
usage: python limits_pick.py map | c30 <ood_h|ood_o|dev_x>"""
import glob
import json
import os
import sys
from collections import defaultdict

from harvest.sim.tasks import X_STEPS

X = "/data/harvest/out/teach_l8d/collect"


def eligible(root):
    out = []
    for d in glob.glob(os.path.join(root, "*", "*_s*")):
        p = os.path.join(d, "scene.json")
        if not os.path.exists(p):
            continue
        s = json.load(open(p))
        if s["task"] in X_STEPS or s.get("furniture"):
            continue
        out.append((int(s["seed"]), d))
    return sorted(out)


if sys.argv[1] == "map":
    for v, n in (("drx_tz0.980", 4), ("drx_tz0.740", 2)):
        eps = eligible(os.path.join(X, "ood_h"))
        print(" ".join([d for _, d in eps if os.path.basename(os.path.dirname(d)) == v][:n]))
elif sys.argv[1] == "v2set":  # 30 dev_x: every container-place ('bin') task episode up to 15, others to 30, even
    eps = eligible(os.path.join(X, "dev_x"))
    task = {d: json.load(open(os.path.join(d, "scene.json")))["task"] for _, d in eps}
    b = [d for _, d in eps if "bin" in task[d]]
    o = [d for _, d in eps if "bin" not in task[d]]
    nb = min(15, len(b))
    pick = [b[int(i * len(b) / nb)] for i in range(nb)] + [o[int(i * len(o) / (30 - nb))] for i in range(30 - nb)]
    g = defaultdict(list)
    for d in pick:
        g[os.path.dirname(d)].append(d)
    for k2 in sorted(g):
        print(" ".join(g[k2]))
else:
    eps = eligible(os.path.join(X, sys.argv[2]))
    k = len(eps) / 30.0
    pick = [eps[int(i * k)][1] for i in range(min(30, len(eps)))]
    g = defaultdict(list)
    for d in pick:
        g[os.path.dirname(d)].append(d)
    for k2 in sorted(g):
        print(" ".join(g[k2]))
