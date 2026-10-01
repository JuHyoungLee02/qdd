"""L9 production re-deal (pod): the jobs of a running production that no lane has claimed yet get new rows over the
current G1 pass list (stratified, arms unchanged per job: job ids r* / l*), new seeds from --start; claimed / done jobs
keep their rows. run9 reads the plan at every job start, so the change reaches the next jobs without a restart.
The plan file is replaced atomically. usage:
  python tools/l9/replan.py <run dir> <g1 pass json>... --start 1100000 [--dry]"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plan as PL  # noqa: E402
from harvest.l9 import task9 as T  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
start = int(sys.argv[sys.argv.index("--start") + 1]) if "--start" in sys.argv else 1100000
args = [a for a in args if a != str(start)]
R, passes = args[0], args[1:]
names = []
for p in passes:
    for k in json.load(open(p))["pass"]:
        if k in T.DEFS and k not in names:
            names.append(k)
plan_p = os.path.join(R, "plan_prod.json")
rows = json.load(open(plan_p))
claimed = set(os.listdir(os.path.join(R, "claim"))) | set(os.listdir(os.path.join(R, "done")))
by_job = defaultdict(list)
for r in rows:
    by_job[r["job"]].append(r)
free = [j for j in sorted(by_job) if j not in claimed]
ft = PL.features()
pairs = {k: [fr for fr in PL.S9.all_rules() if PL.compat(T.DEFS[k], ft[fr])] for k in names}
names = [k for k in names if pairs[k]]
seed, i = start, 0
out = [r for r in rows if r["job"] not in set(free)]
for j in free:
    arm = "right" if j.startswith("r") else "left"
    old = by_job[j]
    for r in old:
        k = names[i % len(names)]
        f, rule = pairs[k][(i // len(names)) % len(pairs[k])]
        out.append({"seed": seed, "arm": arm, "family": f, "rule": rule, "def": k, "split": "train",
                    "style": PL.style_of(seed), "job": j, "pool": r["pool"], "rooms": r["rooms"]})
        seed += 1
        i += 1
print(json.dumps({"definitions": len(names), "free_jobs": len(free), "rows_redealt": i, "seeds": [start, seed - 1]}))
if "--dry" not in sys.argv:
    tmp = plan_p + ".tmp"
    json.dump(out, open(tmp, "w"))
    os.replace(tmp, plan_p)
