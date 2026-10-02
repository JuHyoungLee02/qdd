"""L9 v2 production plan for one robot (pure): successes `--total` over every runnable definition (alloc9 family
weights, >= --min-per-def each, held-out definitions ~5 %), rows = successes / yield (yields from a gate_v2 json,
default 0.5), arms by alloc9's right share, jobs of one (robot, arm); `--ext-share` of the jobs carry ext_p 1.0
(external camera lanes, L9v2-CAM: whole jobs, not a per-episode coin).
usage: python tools/l9/plan_prod_v2.py <out dir> <lanes> --robot ffw_sg2 --total 6000 [--min-per-def 25]
       [--yields gate.json] [--start 4000000] [--job-size 20] [--pool0 6000] [--ext-share 0.3] [--pod DIR]"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import alloc9 as AL  # noqa: E402
from harvest.l9 import scene9 as S9  # noqa: E402
from harvest.l9 import task9v2 as V2  # noqa: E402
from tools.l9 import plan as PL  # noqa: E402


def main():
    out, lanes = sys.argv[1], int(sys.argv[2])
    arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d  # noqa: E731
    robot = arg("--robot", "ffw_sg2")
    use = V2.defs_for([])
    ft = PL.features()
    pairs = {k: [fr for fr in S9.all_rules("train") if PL.compat(d, ft[fr])] for k, d in use.items()}
    defs = {k: d.family for k, d in use.items() if pairs[k]}
    holdout = AL.holdout_defs(defs)
    al = AL.allocate(defs, arg("--total", 6000), arg("--min-per-def", 25), robot_share={robot: 1.0}, holdout=holdout)
    yields = {}
    if "--yields" in sys.argv:
        g = json.load(open(arg("--yields", "")))
        yields = {k: max(v["yield"], 0.2) for k, v in g.get("defs", {}).items() if v.get("n", 0) >= 6}
    rows = AL.plan_rows(al, pairs, arg("--start", 4000000), yields, holdout)
    ch = AL.jobs_v2(rows, arg("--job-size", 20), arg("--pool0", 6000))
    share = arg("--ext-share", 0.3)
    for i, c in enumerate(ch):  # every ~1/share-th job is an external-camera job
        ext = int((i + 1) * share) > int(i * share)
        for r in c:
            r["ext_p"] = 1.0 if ext else 0.0
    res = PL.write(out, rows, ch, lanes, "plan_prod_v2.json", arg("--pod", out))
    res.update(defs=len(defs), holdout=len(holdout), rows=len(rows),
               ext_jobs=sum(1 for c in ch if c[0]["ext_p"] > 0))
    json.dump({"alloc": al, "holdout": holdout, "robot": robot, "total": arg("--total", 6000)},
              open(os.path.join(out, "alloc_prod_v2.json"), "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
