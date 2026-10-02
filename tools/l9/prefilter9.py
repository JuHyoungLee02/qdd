"""Plan prefilter (pure, CPU): replay each row's scene draw (collect9.draw with the job's own pool, no ledger, no
world) and replace rows that would SKIP with "definition does not fit the scene" -- the same definition and seed on
another compatible (environment family, rule) pair that draws -- or drop them. In production half the rows skipped and
a job's ~7 min boot served 9 episodes (10-02 15h). Rows keep their job (pool / rooms / arm / robot / ext unchanged).
usage: python tools/l9/prefilter9.py <plan.json> <out plan.json> [--jobs j1,j2|--jobs-file F] [--workers 8]
       [--alt 6] [--v2-untested]
Prints per-job counts; rows changed carry "prefilter": {"from": [family, rule]}; dropped rows are listed in
<out>.dropped.json."""
import hashlib
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_CTX = {}


def _pairs(defn_id):
    from harvest.l9 import scene9 as S9
    from harvest.l9 import task9v2 as V2
    from tools.l9 import plan as PL
    if "ft" not in _CTX:
        _CTX["ft"] = PL.features()
        _CTX["defs"] = V2.defs_for([])
    d = _CTX["defs"].get(defn_id)
    if d is None:
        return []
    return [fr for fr in S9.all_rules("train") if PL.compat(d, _CTX["ft"][fr])]


def fits(row, pool, rm) -> bool:
    from harvest.l9 import collect9 as C9
    from harvest.l9.collect9 import NoEpisode
    try:
        C9.draw(row, pool, rm, None, tries=int(row.get("draw_tries", 20)), world=None)
        return True
    except (NoEpisode, RuntimeError, ValueError):
        return False


def do_job(args):
    rows, n_alt, untested = args
    from harvest.l9 import reach9 as R9
    from harvest.l9.arm import apply_arm_workspace
    from harvest.l9.run9 import job_pool
    robot = rows[0].get("robot") or "ffw_sg2"
    apply_arm_workspace(rows[0]["arm"])
    pool = job_pool(rows, robot, True, untested)
    rm = R9.load_default()
    keep, dropped, changed = [], [], 0
    for r in rows:
        if fits(r, pool, rm):
            keep.append(r)
            continue
        alts = [fr for fr in _pairs(r["def"]) if tuple(fr) != (r["family"], r["rule"])]
        alts.sort(key=lambda fr: hashlib.sha256(f"{r['seed']}|{fr[0]}|{fr[1]}".encode()).hexdigest())
        for fam, rule in alts[:n_alt]:
            r2 = dict(r, family=fam, rule=rule, prefilter={"from": [r["family"], r["rule"]]})
            if fits(r2, pool, rm):
                keep.append(r2)
                changed += 1
                break
        else:
            dropped.append(r)
    return rows[0]["job"], keep, dropped, changed


def main():
    a = sys.argv[1:]
    arg = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    plan, out = a[0], a[1]
    rows = json.load(open(plan))
    want = None
    if "--jobs" in a:
        want = set(arg("--jobs", "").split(","))
    elif "--jobs-file" in a:
        want = {x.strip() for x in open(arg("--jobs-file", "")) if x.strip()}
    by = {}
    for r in rows:
        if want is None or r["job"] in want:
            by.setdefault(r["job"], []).append(r)
    jobs = list(by.values())
    res_rows, res_drop = [], []
    with Pool(arg("--workers", 8)) as p:
        for job, keep, dropped, changed in p.imap(do_job, [(j, arg("--alt", 6), "--v2-untested" in a) for j in jobs]):
            res_rows += keep
            res_drop += dropped
            print(json.dumps({"job": job, "rows": len(keep) + len(dropped), "kept": len(keep) - changed,
                              "moved": changed, "dropped": len(dropped)}), flush=True)
    json.dump(res_rows, open(out, "w"))
    json.dump(res_drop, open(out + ".dropped.json", "w"))
    print(json.dumps({"jobs": len(jobs), "rows_out": len(res_rows), "dropped": len(res_drop)}))


if __name__ == "__main__":
    main()
