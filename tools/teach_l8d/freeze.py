"""Freeze an L8-D / L8-X bundle: the finished episodes (meta.json present) of <root> (= collect/<split>) whose task is in
the allowed set, optionally without lift / furniture episodes -> a manifest (relative episode paths + counts).
usage: python freeze.py <collect root>/<split> <manifest.json> <tasks: phase1|x|multi|all[,..]> [--no-lift]
  [--no-furniture] [--name NAME]
The builder then reads only these episodes (tools/teach_l8d/build.py --manifest), so later episodes never leak into
a frozen bundle."""
import glob
import hashlib
import json
import os
import sys
from collections import Counter

from harvest.teach_l8d import spec as S

root, out, tasks = sys.argv[1], sys.argv[2], sys.argv[3]
name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else os.path.basename(out)
allow = set()
for t in tasks.split(","):
    allow |= {"phase1": set(S.PHASE1_TASKS), "x": set(S.X_TRAIN_TASKS), "multi": set(S.X_MULTI_TASKS),
              "all": set(S.PHASE1_TASKS) | set(S.X_TRAIN_TASKS) | set(S.X_MULTI_TASKS) | set(S.X_FURNITURE_ONLY)}[t]
eps = []
for m in sorted(glob.glob(os.path.join(root, "*", "*", "meta.json"))):
    ep = os.path.dirname(m)
    sc = json.load(open(os.path.join(ep, "scene.json")))
    if sc["task"] not in allow:
        continue
    if "--no-lift" in sys.argv and sc.get("lift") is not None:
        continue
    if "--no-furniture" in sys.argv and sc.get("furniture"):
        continue
    eps.append((os.path.relpath(ep, root), sc, json.load(open(m))))
rel = [e[0] for e in eps]
digest = hashlib.sha256("\n".join(rel).encode()).hexdigest()[:16]
counts = {"episodes": len(eps), "success": sum(bool(m["success"]) for _, _, m in eps),
          "by_task": dict(sorted(Counter(s["task"] for _, s, _ in eps).items())),
          "by_table_z": dict(sorted(Counter(f"{s['table_z']:.3f}" for _, s, _ in eps).items())),
          "by_height_bin": dict(sorted(Counter(S.height_bin(s["table_z"]) for _, s, _ in eps).items())),
          "by_dist_bin": dict(sorted(Counter(S.dist_bin(s["distractors"]["n"]) for _, s, _ in eps).items())),
          "by_variant": dict(sorted(Counter(s["variant"] for _, s, _ in eps).items())),
          "by_style": dict(sorted(Counter(m["style"] for _, _, m in eps).items())),
          "clean_success_by_task": {t: [sum(1 for _, s, m in eps if s["task"] == t and m["style"] == "clean"),
                                        sum(1 for _, s, m in eps if s["task"] == t and m["style"] == "clean"
                                            and m["success"])] for t in sorted({s["task"] for _, s, _ in eps})}}
json.dump({"schema": "qdd.l8d.bundle/v1", "name": name, "root": root, "digest": digest, "counts": counts,
           "episodes": rel}, open(out, "w"), indent=0)
print(json.dumps({"name": name, "digest": digest, **counts}, indent=1))
