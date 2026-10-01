"""L9R pilot plan (pure; pod with the venv python): rows for the AI Worker head-camera pilot (hcam rand, both arms)
and the Franka pilot (right arm), cut from the production plan (same definition / family / rule / pool / rooms
combinations, new seeds so no production episode is repeated).
usage: python tools/l9r/pilot_plan.py <prod plan.json> <out dir> [--ffw-defs=15] [--franka-defs=20] [--n=10]
       [--smoke [--smoke-defs=a,b]]   (smoke: 2 FFW rand rows + 2 Franka rows)
       [--eval --defs-ffw=a,b,.. --defs-franka=c,d,.. [--n-eval=300]]  (E-HCAM8 hold-out sets ii-a / ii-b / L9 std)
-> <out dir>/plan.json, <out dir>/jobs.txt ("--plan P --job J" per job, 10 rows a job, one arm / robot each)"""
import json
import os
import random
import sys
from collections import defaultdict

SEED_OFFSET = 70_000_000  # pilot seeds: production seed + offset (production seeds are < 2e6)
EVAL_OFFSET = 8_000_000  # E-HCAM8 hold-out seeds 9e6+ (production seeds 1.0-1.3e6)


def pick_defs(rows, k, rng):
    by_fam = defaultdict(set)
    for r in rows:
        by_fam[r["family"]].add(r["def"])
    fams = sorted(by_fam)
    out, i = [], 0
    pools = {f: sorted(by_fam[f]) for f in fams}
    for f in fams:
        rng.shuffle(pools[f])
    while len(out) < k and any(pools.values()):
        f = fams[i % len(fams)]
        if pools[f]:
            d = pools[f].pop()
            if d not in out:
                out.append(d)
        i += 1
    return out


def rows_for(prod, defs, n, arms, robot, hcam, rng, tag, offset=SEED_OFFSET):
    out = []
    for d in defs:
        cand = [r for r in prod if r["def"] == d and r["arm"] in arms]
        rng.shuffle(cand)
        per_arm = defaultdict(int)
        for r in cand:
            a = r["arm"]
            if per_arm[a] >= (n + len(arms) - 1) // len(arms) or sum(per_arm.values()) >= n:
                continue
            per_arm[a] += 1
            row = dict(r, seed=int(r["seed"]) + offset, robot=robot)
            if hcam:
                row["hcam"] = hcam
            out.append(row)
    # jobs: one arm each, 10 rows a job, the job's first row decides pool / rooms (run9): set them per job
    jobs = []
    for a in sorted(arms):
        mine = [r for r in out if r["arm"] == a]
        for j in range(0, len(mine), 10):
            chunk = mine[j:j + 10]
            jid = f"{tag}{a[0]}{j // 10:03d}"
            for r in chunk:
                r.update(job=jid, pool=chunk[0]["pool"], rooms=chunk[0]["rooms"])
            jobs.append(jid)
    return out, jobs


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    opt = {x.split("=")[0]: x.split("=")[1] for x in sys.argv[1:] if x.startswith("--") and "=" in x}
    prod, out_dir = json.load(open(a[0])), a[1]
    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(20261001)
    n = int(opt.get("--n", 10))
    if "--eval" in sys.argv:  # prereg_hcam8 §4: hold-out seeds (9e6 + production seed), defs given
        fd, kd = opt["--defs-ffw"].split(","), opt["--defs-franka"].split(",")
        ne = int(opt.get("--n-eval", 300))
        per_f, per_k = -(-ne // len(fd)), -(-ne // len(kd))
        f_rows, f_jobs = rows_for(prod, fd, per_f, ("right", "left"), "ffw_sg2", "hold", rng, "ea", EVAL_OFFSET)
        k_rows, k_jobs = rows_for(prod, kd, per_k, ("right",), "franka_mast", None, rng, "eb", EVAL_OFFSET)
        s_rows, s_jobs = rows_for(prod, fd, per_f, ("right", "left"), "ffw_sg2", None, rng, "ec", EVAL_OFFSET + 1)
        f_rows, f_jobs = f_rows + s_rows, f_jobs + s_jobs
    elif "--smoke" in sys.argv:
        defs = opt["--smoke-defs"].split(",") if "--smoke-defs" in opt else pick_defs(prod, 2, rng)
        f_rows, f_jobs = rows_for(prod, defs[:1], 2, ("right",), "ffw_sg2", "rand", rng, "sf")
        k_rows, k_jobs = rows_for(prod, defs[1:2], 2, ("right",), "franka_mast", None, rng, "sk")
    else:
        fd = pick_defs(prod, int(opt.get("--ffw-defs", 15)), rng)
        kd = pick_defs(prod, int(opt.get("--franka-defs", 20)), random.Random(20261002))
        f_rows, f_jobs = rows_for(prod, fd, n, ("right", "left"), "ffw_sg2", "rand", rng, "pf")
        k_rows, k_jobs = rows_for(prod, kd, n, ("right",), "franka_mast", None, rng, "pk")
    plan = os.path.join(out_dir, "plan.json")
    json.dump(f_rows + k_rows, open(plan, "w"))
    # interleave the two pilots so both finish together
    order = [j for pair in zip(k_jobs, f_jobs) for j in pair] + k_jobs[len(f_jobs):] + f_jobs[len(k_jobs):]
    with open(os.path.join(out_dir, "jobs.txt"), "w") as f:
        for j in order:
            f.write(f"--plan {plan} --job {j}\n")
    print(json.dumps({"ffw_rows": len(f_rows), "ffw_jobs": len(f_jobs), "franka_rows": len(k_rows),
                      "franka_jobs": len(k_jobs), "ffw_defs": sorted({r['def'] for r in f_rows}),
                      "franka_defs": sorted({r['def'] for r in k_rows})}))


if __name__ == "__main__":
    main()
