"""Quota filter for L9 single-arm plan rows (pure; main 10-02 16h: robots balanced ~25 % each, per-definition caps).
Drops rows of a (robot, definition) cell once its expected successes reach the cell cap, and of a robot once the robot
cap is reached. expected = gate-passing successes so far + yield(robot) x pending rows (queued, not yet run) + yield x
rows kept here (in order).
usage: python tools/l9/capfilter9.py <rows in.json> <rows out.json> --collect R1,R2 --pending plan[@collect[@run]],...
       [--robot-cap ffw_sg2=2600,franka_mast=3700,r1pro=2500,g1=2200] [--cell-cap 0 = per robot] [--n-defs 198]
       [--yield 0.5] [--batch <job list file: pending rows of these jobs are not counted>]
pending plans: rows whose episode dir has neither meta.json nor skipped.json count as pending."""
import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9.run9 import ep_dir  # noqa: E402

CAPS = {"ffw_sg2": 2600, "franka_mast": 3700, "r1pro": 2500, "g1": 2200}


def done_counts(roots):
    cell, rob, eps = Counter(), Counter(), Counter()
    for root in roots:
        for m in glob.glob(os.path.join(root, "*", "*", "*", "meta.json")):
            try:
                meta = json.load(open(m))
            except ValueError:
                continue
            if meta.get("grasp_v2") is None:
                continue
            r = meta.get("robot") or "ffw_sg2"
            eps[r] += 1
            if meta.get("success") and (meta.get("max_dq_rad") or 0) <= 0.04:
                cell[(r, meta.get("task_id"))] += 1
                rob[r] += 1
    return cell, rob, eps


def main():
    a = sys.argv[1:]
    arg = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    rows = json.load(open(a[0]))
    roots = [x for x in arg("--collect", "").split(",") if x]
    caps = dict(CAPS)
    for kv in [x for x in arg("--robot-cap", "").split(",") if x]:
        k, v = kv.split("=")
        caps[k] = int(v)
    n_defs = arg("--n-defs", 198)
    fixed = arg("--cell-cap", 0)  # 0: per robot, 1.15 x robot cap / definitions (room for defs a robot cannot do)
    cell_cap = {r: (fixed or max(8, round(1.15 * c / n_defs))) for r, c in caps.items()}
    cell, rob, eps = done_counts(roots)
    yld = {r: (rob[r] / eps[r] if eps[r] >= 50 else arg("--yield", 0.5)) for r in set(eps) | set(caps)}
    exp_cell = Counter({k: float(v) for k, v in cell.items()})
    exp_rob = Counter({k: float(v) for k, v in rob.items()})
    skip_jobs = {x.strip() for x in open(arg("--batch", ""))} if "--batch" in a else set()
    for spec in [x for x in arg("--pending", "").split(",") if x]:
        p, out_dir, run = (spec.split("@") + [None, None])[:3]  # plan[@collect dir[@run dir]]
        if not os.path.exists(p):
            continue
        out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(p)), "collect")
        for r in json.load(open(p)):
            if r["job"] in skip_jobs:  # the batch being filtered now (its rows are decided below)
                continue
            if run:  # jobs replaced by the prefilter (claim lane 'superseded*') or finished never run these rows
                c = os.path.join(run, "claim", r["job"], "lane")
                if os.path.exists(os.path.join(run, "done", r["job"])) or (
                        os.path.exists(c) and open(c).read().startswith("superseded")):
                    continue
            d = ep_dir(out_dir, r)
            if os.path.exists(os.path.join(d, "meta.json")) or os.path.exists(os.path.join(d, "skipped.json")):
                continue
            rb = r.get("robot") or "ffw_sg2"
            exp_cell[(rb, r["def"])] += yld.get(rb, 0.5)
            exp_rob[rb] += yld.get(rb, 0.5)
    keep, drop = [], Counter()
    for r in rows:
        rb = r.get("robot") or "ffw_sg2"
        if exp_rob[rb] >= caps.get(rb, 10 ** 9):
            drop["robot_cap"] += 1
            continue
        if exp_cell[(rb, r["def"])] >= cell_cap.get(rb, 15):
            drop["cell_cap"] += 1
            continue
        keep.append(r)
        exp_cell[(rb, r["def"])] += yld.get(rb, 0.5)
        exp_rob[rb] += yld.get(rb, 0.5)
    json.dump(keep, open(a[1], "w"))
    print(json.dumps({"in": len(rows), "kept": len(keep), "dropped": dict(drop),
                      "expected_by_robot": {k: round(v) for k, v in exp_rob.items()}, "cell_cap": cell_cap,
                      "yield": {k: round(v, 2) for k, v in yld.items()}}))


if __name__ == "__main__":
    main()
