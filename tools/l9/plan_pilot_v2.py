"""L9 v2 pilot plan for one robot: every definition runnable now (task9v2.defs_for(caps)) x `per` attempts, arms dealt
by alloc9's right share, (family, rule) pairs round-robin, jobs of `job_size` rows of one (robot, arm).
usage: python tools/l9/plan_pilot_v2.py <out dir> <lanes> --robot ffw_sg2 [--per 10] [--start 3900000]
       [--caps a,b] [--job-size 10] [--pod DIR] [--defs a,b] [--pool0 5000]
Writes <out>/plan_pilot_v2.json and jobs_<k>.txt (pure)."""
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
    robot, per = arg("--robot", "ffw_sg2"), arg("--per", 10)
    caps = [c for c in arg("--caps", "").split(",") if c]
    use = V2.defs_for(caps)
    if "--defs" in sys.argv:
        keep = set(arg("--defs", "").split(","))
        use = {k: d for k, d in use.items() if k in keep}
    ft = PL.features()
    pairs = {k: [fr for fr in S9.all_rules("train") if PL.compat(d, ft[fr])] for k, d in use.items()}
    defs = {k: d.family for k, d in use.items() if pairs[k]}
    al = AL.allocate(defs, per * len(defs), per, robot_share={robot: 1.0})
    rows = AL.plan_rows(al, pairs, arg("--start", 3900000), {k: 1.0 for k in defs})
    for r in rows:
        # pilot: training pools (the pilot's successes may train, like v1 pilots) -- except the frozen hold-out
        # definitions, never train rows (owner 10-02: this line wrote them as train, E-TP1 leak)
        r["split"] = "holdout" if AL.is_holdout(r["def"]) else "train"
        r["pilot"] = True
    ch = AL.jobs_v2(rows, arg("--job-size", 10), arg("--pool0", 5000))
    res = PL.write(out, rows, ch, lanes, "plan_pilot_v2.json", arg("--pod", out))
    res.update(defs=len(defs), no_scene=sorted(k for k, p in pairs.items() if not p))
    print(json.dumps(res))


if __name__ == "__main__":
    main()
