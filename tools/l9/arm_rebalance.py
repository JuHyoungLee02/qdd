"""Left / right rebalance of a plan's not-yet-claimed jobs (pure; user 10-02: dual-arm robots use each arm 50 % +-5 pp
per robot and per definition). Counts per (robot, definition, arm) what is done (gate-passing successes in the collect
roots) plus what is already installed (filtered plans), then walks the unclaimed jobs of the source plan and flips a
whole job's arm (rows' "arm", job id suffix _l / _r) when its arm is ahead for the job's definitions. Jobs stay one arm.
usage: python tools/l9/arm_rebalance.py <plan.json> <run dir> <out plan.json> --collect R1,R2 [--installed P1,P2]
       [--yield 0.45]"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict


def main():
    a = sys.argv[1:]
    arg = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    plan, run, out = a[0], a[1], a[2]
    yld = arg("--yield", 0.45)
    cnt = Counter()  # (robot, def, arm) -> expected successes
    for root in [x for x in arg("--collect", "").split(",") if x]:
        for m in glob.glob(os.path.join(root, "*", "*", "*", "meta.json")):
            try:
                meta = json.load(open(m))
            except ValueError:
                continue
            if meta.get("success") and (meta.get("max_dq_rad") or 0) <= 0.04:
                cnt[(meta.get("robot") or "ffw_sg2", meta.get("task_id"), meta.get("arm"))] += 1
    for p in [x for x in arg("--installed", "").split(",") if x and os.path.exists(x)]:
        for r in json.load(open(p)):
            if not os.path.exists(os.path.join(run, "done", r["job"])):
                cnt[(r.get("robot") or "ffw_sg2", r["def"], r["arm"])] += yld
    rows = json.load(open(plan))
    jobs = defaultdict(list)
    for r in rows:
        jobs[r["job"]].append(r)
    flipped, kept, out_rows = 0, 0, []
    for job, rs in jobs.items():
        if os.path.isdir(os.path.join(run, "claim", job)):
            out_rows += rs  # claimed / superseded: untouched
            continue
        arm = rs[0]["arm"]
        other = "left" if arm == "right" else "right"
        rb = rs[0].get("robot") or "ffw_sg2"
        ahead = sum(1 for r in rs if cnt[(rb, r["def"], arm)] > cnt[(rb, r["def"], other)])
        tot_a = sum(v for (b, _, x), v in cnt.items() if b == rb and x == arm)
        tot_o = sum(v for (b, _, x), v in cnt.items() if b == rb and x == other)
        flip = ahead > len(rs) / 2 or (ahead == len(rs) / 2 and tot_a > tot_o)
        new_arm = other if flip else arm
        new_job = job[:-1] + new_arm[0] if flip and job[-2] == "_" else job
        for r in rs:
            out_rows.append(dict(r, arm=new_arm, job=new_job, **({"arm_flipped_from": arm} if flip else {})))
            cnt[(rb, r["def"], new_arm)] += yld
        flipped += flip
        kept += not flip
    json.dump(out_rows, open(out, "w"))
    by = Counter(r["arm"] for r in out_rows if not os.path.isdir(os.path.join(run, "claim", r.get("arm_flipped_from") and r["job"] or r["job"])))
    print(json.dumps({"jobs_flipped": flipped, "jobs_kept": kept, "unclaimed_rows_by_arm": dict(by)}))


if __name__ == "__main__":
    main()
