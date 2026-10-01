"""E-CL15 T1 work list (docs/stage3/prereg_cl15.md; pod, venv_train, no Isaac).
From the E-M35CL L8S held-out list (/data/harvest/out/main35_closed/groups.json, truth-success episodes only), one
episode per task kind (kind = task name before '__'), the first by sha256("cl15:<task>:<seed>"); kinds: the 7 ov_*
kinds + the 3 base kinds with the most such episodes (ties: kind name). -> <root>/t1.json, eps_<group>.json, jobs.txt
(one line per Isaac process: "<group id>\t<job>")."""
from __future__ import annotations

import collections
import hashlib
import json
import os

ROOT = "/data/harvest/out/cl15"
SRC = "/data/harvest/out/main35_closed/groups.json"


def main():
    G = json.load(open(SRC))
    kinds = collections.defaultdict(list)
    for g in G["groups"]:
        if g["id"] == "ood_o58":
            continue
        for e in g["eps"]:
            if e.get("truth_success"):
                h = hashlib.sha256(f"cl15:{e['task']}:{e['seed']}".encode()).hexdigest()
                kinds[e["task"].split("__")[0]].append((h, g["id"], g["job"], e))
    ov = sorted(k for k in kinds if k.startswith("ov_"))
    base = sorted((k for k in kinds if not k.startswith("ov_")), key=lambda k: (-len(kinds[k]), k))[:10 - len(ov)]
    pick = {k: sorted(kinds[k], key=lambda x: x[0])[0] for k in ov + base}
    by_g = collections.defaultdict(list)
    jobs = {}
    for k, (_, gid, job, e) in pick.items():
        by_g[gid].append(dict(e, set="t1", kind=k))
        jobs[gid] = job
    os.makedirs(ROOT, exist_ok=True)
    for gid, eps in by_g.items():
        json.dump(eps, open(os.path.join(ROOT, f"eps_{gid}.json"), "w"))
    with open(os.path.join(ROOT, "jobs.txt"), "w") as f:
        for gid in sorted(by_g, key=lambda g: -len(by_g[g])):
            f.write(f"{gid}\t{jobs[gid]}\n")
    out = {"src": SRC, "src_sha256_16": hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:16],
           "kinds": {k: {"group": v[1], "task": v[3]["task"], "seed": v[3]["seed"], "dir": v[3]["dir"],
                         "n_candidates": len(kinds[k])} for k, v in pick.items()}}
    json.dump(out, open(os.path.join(ROOT, "t1.json"), "w"), indent=1)
    print(json.dumps({"n": len(pick), "groups": {g: len(v) for g, v in by_g.items()}}))


if __name__ == "__main__":
    main()
