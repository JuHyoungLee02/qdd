"""E-CL15c work list (prereg_cl15.md change 3): the 5 T1 episodes the user named (1 bottle_bin, 4 ov_basket,
5 ov_behind, 7 ov_front, 9 ov_left), same seeds / held-out environment as the ep1.5 run, one Isaac process per
episode (so the per-episode budget gate runs before each), cheapest first by the ep1.5 call count.
usage: prep_c.py <root> [kind,kind,..] [jobs file name=jobs.txt]   (reads /data/harvest/out/cl15/t1.json)"""
from __future__ import annotations

import json
import os
import sys

SRC = "/data/harvest/out/cl15"
KINDS = ("bottle_bin", "ov_basket", "ov_behind", "ov_front", "ov_left")


def main():
    root = sys.argv[1]
    want = sys.argv[2].split(",") if len(sys.argv) > 2 else KINDS
    os.makedirs(root, exist_ok=True)
    t1 = json.load(open(os.path.join(SRC, "t1.json")))
    jobs = {ln.split("\t", 1)[0]: ln.rstrip("\n").split("\t", 1)[1] for ln in open(os.path.join(SRC, "jobs.txt"))}
    ep15 = json.load(open(os.path.join(SRC, "summary.json")))["rows"]
    calls = {r["kind"]: r.get("n_calls") or 30 for r in ep15}
    kinds = {k: v for k, v in t1["kinds"].items() if k in want}
    lines = []
    for k in sorted(kinds, key=lambda k: (calls.get(k, 30), k)):
        v = kinds[k]
        eps = [e for e in json.load(open(os.path.join(SRC, f"eps_{v['group']}.json"))) if e["task"] == v["task"]
               and e["seed"] == v["seed"]]
        assert len(eps) == 1, k
        gid = f"{v['group']}__{k}"
        json.dump(eps, open(os.path.join(root, f"eps_{gid}.json"), "w"))
        lines.append(f"{gid}\t{jobs[v['group']]}\n")
    open(os.path.join(root, sys.argv[3] if len(sys.argv) > 3 else "jobs.txt"), "w").write("".join(lines))
    t1p = os.path.join(root, "t1.json")
    old = json.load(open(t1p))["kinds"] if os.path.exists(t1p) else {}
    json.dump(dict(t1, kinds={**old, **kinds}), open(t1p, "w"), indent=1)
    print(json.dumps({"n": len(lines), "order": [ln.split("\t")[0] for ln in lines]}))


if __name__ == "__main__":
    main()
