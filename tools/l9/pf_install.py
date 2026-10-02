"""Install prefiltered jobs (tools/l9/prefilter9.py output) into a running lane queue (pure):
for each job of the filtered rows whose original is still unclaimed, claim the original as 'superseded' (atomic mkdir;
a lane that got there first keeps it and the new version is not installed), add its rows as job 'f'+<job> to
<run>/<plan name> (written atomically), and append its line to <run>/jobs.txt.
usage: python tools/l9/pf_install.py <run dir> <filtered rows json> <plan name, e.g. plan_prodA_f.json> [--p 0.15]
       [--batch <job list file>] [--merge k]  (empty jobs of the batch claimed too; k jobs merged into one)"""
import json
import os
import sys


def main():
    a = sys.argv[1:]
    run, src, name = a[0], a[1], a[2]
    p = a[a.index("--p") + 1] if "--p" in a else "0.15"
    rows = json.load(open(src))
    plan_path = os.path.join(run, name)
    plan = json.load(open(plan_path)) if os.path.exists(plan_path) else []
    have = {r["job"] for r in plan}
    by = {}
    for r in rows:
        by.setdefault(r["job"], []).append(r)
    added, lost, claimed = [], [], []
    for job, rs in by.items():
        if "f" + job in have or "m" + job in have or not rs:
            continue
        try:
            os.makedirs(os.path.join(run, "claim", job))
        except FileExistsError:
            lost.append(job)
            continue
        with open(os.path.join(run, "claim", job, "lane"), "w") as f:
            f.write("superseded\n")
        claimed.append((job, rs))
    # --merge k: k consecutive claimed jobs of one (robot, arm, ext_p, split, hcam) become one job on the first job's
    # pool / rooms (a job's Isaac boot took 11-15 min under load: 20-row jobs spent half their lane time booting)
    k = int(a[a.index("--merge") + 1]) if "--merge" in a else 1
    groups = {}
    for job, rs in claimed:
        r0 = rs[0]
        key = (r0.get("robot"), r0["arm"], r0.get("ext_p"), r0.get("split"), r0.get("hcam"))
        groups.setdefault(key, []).append((job, rs))
    for key, lst in groups.items():
        for i in range(0, len(lst), k):
            part = lst[i:i + k]
            new = ("m" if len(part) > 1 else "f") + part[0][0]
            r0 = part[0][1][0]
            for job, rs in part:
                plan += [dict(r, job=new, superseded=job, pool=r0["pool"], rooms=r0["rooms"]) for r in rs]
            added.append(new)
    empty = 0
    if "--batch" in a:  # jobs of the batch with no row left (every row would skip): claim them so no lane boots them
        for job in (x.strip() for x in open(a[a.index("--batch") + 1]) if x.strip()):
            if job in by:
                continue
            try:
                os.makedirs(os.path.join(run, "claim", job))
            except FileExistsError:
                continue
            with open(os.path.join(run, "claim", job, "lane"), "w") as f:
                f.write("superseded-empty\n")
            empty += 1
    tmp = plan_path + ".tmp"
    json.dump(plan, open(tmp, "w"))
    os.replace(tmp, plan_path)
    with open(os.path.join(run, "jobs.txt"), "a") as f:
        for new in added:
            f.write(f"--plan {plan_path} --job {new} --v2 --p {p}\n")
    print(json.dumps({"added": len(added), "rows": sum(len(rs) for _, rs in claimed), "already_claimed": len(lost),
                      "empty_superseded": empty}))


if __name__ == "__main__":
    main()
