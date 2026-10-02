"""Split integrated-A/B jobs whose rows mix ext_p values (0.0 vs None: run9 refuses them). In place on <ab dir>:
rows of a mixed job keep the job name for the most common ext_p, the others move to <job>x<k>; new jobs are appended to
q.txt (A then B), and the claim of a failed mixed job (no done marker) is removed so a lane runs it again.
usage: python3 fix_mixed_ext.py <ab dir>"""
import json
import os
import shutil
import sys
from collections import Counter, defaultdict

ab = sys.argv[1]
p = os.path.join(ab, "plan_gab.json")
plan = json.load(open(p))
by = defaultdict(list)
for r in plan:
    by[r["job"]].append(r)
new_q = []
for job, rows in sorted(by.items()):
    vals = Counter(repr(r.get("ext_p")) for r in rows)
    if len(vals) < 2:
        continue
    keep = vals.most_common(1)[0][0]
    others = sorted(v for v in vals if v != keep)
    for k, v in enumerate(others):
        nj = f"{job}x{k}"
        for r in rows:
            if repr(r.get("ext_p")) == v:
                r["job"] = nj
        for arm in ("A", "B"):
            new_q.append(f"{arm} {rows[0]['robot']} {p} {nj}\n")
    for arm in ("A", "B"):
        c = os.path.join(ab, "claim", f"{arm}_{job}")
        if os.path.isdir(c) and not os.path.exists(os.path.join(ab, "done", f"{arm}_{job}")):
            shutil.rmtree(c)
            new_q.append(f"{arm} {rows[0]['robot']} {p} {job}\n")  # lanes read q.txt once: queue it again
            print("unclaimed", arm, job)
    print("split", job, dict(vals), "->", others)
shutil.copy(p, p + ".bak_mixed")
json.dump(plan, open(p + ".tmp", "w"))
os.replace(p + ".tmp", p)
with open(os.path.join(ab, "q.txt"), "a") as f:
    f.writelines(new_q)
print("appended", len(new_q))
