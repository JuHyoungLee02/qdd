"""Y-stratified seed selection for new L9 v2 plan rows (pure, CPU).

Root cause (10-02, tools/l9/diversity9.py vs v1 /data/harvest/out/l9/prod1/collect): the AI Worker target-y spread
in v2 successes is narrower than v1's per-definition median (std_y ~0.25 vs ~0.27, iqr_y ~0.43 vs ~0.50). Checked:
(1) success-vs-all-episode filtering changes nothing (0.252 vs 0.254 std_y) -- the gate is not the cause;
(2) old (v1-shared) vs new (v2-only) definitions are equally narrow (0.433 vs 0.455 median iqr_y) -- the new
task9v2 definitions are not the cause; (3) a pure-CPU replay of collect9.draw() on current plan rows (no Isaac,
no runtime grasp/SkipScene filter at all) already reproduces the same narrow spread as the recorded episodes --
the scene9/task9 sampler's OWN first-fit draw is already this narrow, before any runtime filtering. So the fix
belongs at the draw/seed-selection stage, not at prefilter/capfilter/gate.

Fix: collect9.draw() already explores candidate sub-seeds on retry (sd = seed + 100003 * k, k = 0..tries-1) when
the first one does not fit the scene. This script evaluates --k of those SAME candidate sub-seeds per row (pure
CPU, no world) and keeps the one whose first-target |y| (distance from centre, sign-free) is closest to a quantile
target drawn from v1's OWN pooled |y| distribution for that robot (a deterministic function of the row's seed, so
results are reproducible and do not pile up at the extremes -- a "range move" against the v1 reference, never a
hardcoded constant, matching L9 owner principle: robot-specific adjustments are a range shift, not a constant).
Magnitude, not signed y: a row's arm fixes the sign of its achievable placements (the furniture is built off-centre
towards the working arm, scene9._yc), so targeting raw signed y from both-arm-pooled v1 data asks about half of all
rows for an unreachable sign and collapses them onto the band edge nearest zero -- verified narrower, not wider,
before this fix. Targeting |y| keeps each row's own natural sign and only steers how far from centre it lands.
Only "seed" may change, and only to a value collect9.draw() would already have tried on retry for this exact row --
no new collision risk, no change to robot/arm/def/family/rule/job/pool, no change to any quality gate. Rows that
fail every candidate keep seed k=0 (the already-prefiltered, known-fitting value).

usage: python tools/l9/ystrat9.py <plan.json> <out plan.json> --ref <v1 collect root> [--k 8] [--workers 8]
       [--jobs j1,j2 | --jobs-file F]
Prints per-job {rows, reseeded} and an overall summary. Insert between tools/l9/prefilter9.py and
tools/l9/capfilter9.py (new rows only; do not re-run on rows already claimed/running).
"""
import glob
import hashlib
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SUBSEED_STRIDE = 100003  # = harvest.l9.collect9.draw's own retry stride (sd = seed + 100003 * k)
BASE_X = {"r1pro": -0.05, "g1": -0.02}


def _h(*p) -> float:
    return int(hashlib.sha256(":".join(map(str, p)).encode()).hexdigest()[:12], 16) / float(16 ** 12)


def ref_y_by_robot(roots, min_n=5):
    """{robot: sorted np.array of target y} from a v1-style collect root (success & max_dq_rad <= 0.04, same
    filter as tools/l9/diversity9.py's default), pooled over every definition with >= min_n episodes."""
    import numpy as np
    from collections import defaultdict
    per_robot = defaultdict(list)
    per_cell = defaultdict(list)
    for root in roots:
        for m in glob.glob(os.path.join(root, "*", "*", "*", "meta.json")):
            d = os.path.dirname(m)
            try:
                meta = json.load(open(m))
                sc = json.load(open(os.path.join(d, "scene.json")))
                row0 = json.loads(open(os.path.join(d, "labels.jsonl")).readline())
            except (OSError, ValueError):
                continue
            if not (meta.get("success") and (meta.get("max_dq_rad") or 0) <= 0.04):
                continue
            robot = meta.get("robot") or "ffw_sg2"
            lay = sc.get("layout") or {}
            tg = row0.get("tgt")
            if tg not in lay:
                continue
            per_cell[(robot, meta.get("task_id"))].append(float(lay[tg][1]))
    for (robot, _task), ys in per_cell.items():
        if len(ys) >= min_n:
            per_robot[robot].extend(ys)
    # magnitude only (|y|, "distance from centre"): a row's arm fixes the SIGN of its achievable y (the furniture
    # is built off-centre towards the working arm, harvest.l9.scene9._yc), so a target drawn from v1's raw,
    # both-arm-pooled y would be unreachable (wrong sign) for about half of all rows, and "closest candidate"
    # would then collapse onto the band edge nearest zero -- narrowing instead of widening (caught by verification:
    # the raw-y version measured *narrower* than the unmodified baseline). Magnitude is sign-free, so every row's
    # own natural sign is kept, only how far from centre is steered toward v1's own distribution.
    return {r: np.sort(np.abs(np.asarray(ys, float))) for r, ys in per_robot.items() if ys}


def y_target(ref_sorted, u: float) -> float:
    """-> a target |y| (distance from centre), the u-th quantile of v1's own |y| distribution."""
    import numpy as np
    if ref_sorted is None or len(ref_sorted) == 0:
        return 0.0
    return float(np.percentile(ref_sorted, 100.0 * u))


def draw_y(row, pool, rm):
    """-> target y (robot frame) of this exact row's draw, or None if it does not fit."""
    from harvest.l9.collect9 import draw, NoEpisode
    try:
        sc, ep, light, head, h, sd = draw(row, pool, rm, None, tries=1, world=None)
    except (NoEpisode, RuntimeError, ValueError):
        return None
    steps = ep.get("step_info") or []
    lay = ep.get("objects") or {}
    if not steps or steps[0].get("target") not in lay:
        return None
    x, y = lay[steps[0]["target"]]["xy"]
    return float(y)


def do_job(args):
    rows, k_max, ref = args
    from harvest.l9 import reach9 as R9
    from harvest.l9.arm import apply_arm_workspace
    from harvest.l9.run9 import job_pool
    robot = rows[0].get("robot") or "ffw_sg2"
    apply_arm_workspace(rows[0]["arm"])
    pool = job_pool(rows, robot, True, False)
    rm = R9.load_default()
    ref_sorted = ref.get(robot)
    out, reseeded = [], 0
    for r in rows:
        base = int(r["seed"])
        u = _h("ystrat9", base)
        target = y_target(ref_sorted, u)  # target |y| (sign-free); each candidate keeps its own natural sign
        best_k, best_y, best_err = 0, None, None
        for k in range(k_max):
            r2 = dict(r, seed=base + SUBSEED_STRIDE * k)
            y = draw_y(r2, pool, rm)
            if y is None:
                continue
            err = abs(abs(y) - target)
            if best_err is None or err < best_err:
                best_k, best_y, best_err = k, y, err
        r_out = dict(r)
        if best_k != 0:
            r_out["seed"] = base + SUBSEED_STRIDE * best_k
            r_out["ystrat"] = {"k": best_k, "y": round(best_y, 4), "target": round(target, 4), "base_seed": base}
            reseeded += 1
        out.append(r_out)
    return rows[0]["job"], out, reseeded


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
    ref_roots = [x for x in arg("--ref", "").split(",") if x]
    ref = ref_y_by_robot(ref_roots) if ref_roots else {}
    k_max = arg("--k", 8)
    res_rows, total_reseeded = [], 0
    with Pool(arg("--workers", 8)) as p:
        for job, out_rows, reseeded in p.imap(do_job, [(j, k_max, ref) for j in jobs]):
            res_rows += out_rows
            total_reseeded += reseeded
            print(json.dumps({"job": job, "rows": len(out_rows), "reseeded": reseeded}), flush=True)
    json.dump(res_rows, open(out, "w"))
    print(json.dumps({"jobs": len(jobs), "rows_out": len(res_rows), "reseeded": total_reseeded,
                      "ref_robots": {r: len(v) for r, v in ref.items()}}))


if __name__ == "__main__":
    main()
