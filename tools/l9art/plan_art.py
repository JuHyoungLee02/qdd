"""Plan rows for the articulated runner (pure): python tools/l9art/plan_art.py --out plan.json --defs a,b --n 20
--robots ffw_sg2,franka_mast [--seed0 9100000] [--per-job 12] [--split train] [--tag pilot]
Every (def, robot) gets n rows; AI Worker rows alternate right / left arms; rows are grouped into jobs of one
(robot, arm) with mixed definitions (each job = one fixture set)."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.l9art import tasks as TK  # noqa: E402


def plan(defs, n, robots, seed0, per_job, split, tag, arms_aiw=("right", "left")):
    rows = []
    s = seed0
    for d in defs:
        for rb in robots:
            if rb not in TK.DEFS[d]["robots"]:
                continue
            for i in range(n):
                arm = arms_aiw[i % len(arms_aiw)] if rb in ("ffw_sg2", "r1pro") else "right"
                rows.append({"seed": s, "def": d, "robot": rb, "arm": arm, "split": split})
                s += 1
    groups = {}
    for r in rows:
        groups.setdefault((r["robot"], r["arm"]), []).append(r)
    out = []
    for (rb, arm), rs in sorted(groups.items()):
        rs = sorted(rs, key=lambda r: (r["seed"] * 2654435761) % 4294967296)  # mix definitions inside a job
        for j in range(0, len(rs), per_job):
            job = f"{tag}_{rb}_{arm[0]}_{j // per_job:03d}"
            for k, r in enumerate(rs[j:j + per_job]):
                out.append(dict(r, job=job, pool=(j // per_job) % 40, rooms=(j // per_job + 3) % 50))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--defs", default=",".join(sorted(TK.DEFS)))
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--robots", default="ffw_sg2,franka_mast")
    ap.add_argument("--seed0", type=int, default=9100000)
    ap.add_argument("--per-job", type=int, default=12)
    ap.add_argument("--split", default="train")
    ap.add_argument("--tag", default="art")
    ap.add_argument("--pod-plan", default=None, help="also write <out>_lane_jobs.txt for tools/l9/lane.sh: \"--plan <pod-plan> --job J\" per line")
    a = ap.parse_args(argv)
    rows = plan(a.defs.split(","), a.n, a.robots.split(","), a.seed0, a.per_job, a.split, a.tag)
    json.dump(rows, open(a.out, "w"), indent=0)
    jobs = sorted({r["job"] for r in rows})
    print(json.dumps({"rows": len(rows), "jobs": len(jobs)}))
    with open(os.path.splitext(a.out)[0] + "_jobs.txt", "w", newline="\n") as f:  # LF: pod lanes read it
        f.write("\n".join(jobs) + "\n")
    if a.pod_plan:  # lane.sh appends "--out <run dir>/collect" itself
        with open(os.path.splitext(a.out)[0] + "_lane_jobs.txt", "w", newline="\n") as f:
            f.write("".join(f"--plan {a.pod_plan} --job {j}\n" for j in jobs))


if __name__ == "__main__":
    main()
