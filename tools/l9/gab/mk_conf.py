"""Confirmation A/B dir (coordinator 10-03): rows = whole jobs of main2's plan until each robot has >= N rows (same seeds),
A.env = main2 B.env, B.env = A.env + place prescription + short-arm mechanisms. usage: python3 mk_conf.py <code dir> <out> <N>"""
import json
import os
import shutil
import sys
from collections import defaultdict

code, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
src = "/data/harvest/l9v2/gab/main2"
plan = json.load(open(os.path.join(src, "plan_gab.json")))
jobs = defaultdict(list)
for r in plan:
    jobs[(r["robot"], r["job"])].append(r)
cnt, keep = defaultdict(int), []
for (robot, job), rows in sorted(jobs.items()):
    if cnt[robot] < n:
        keep.extend(rows)
        cnt[robot] += len(rows)
os.makedirs(os.path.join(out, "A"), exist_ok=True)
os.makedirs(os.path.join(out, "B"), exist_ok=True)
p = os.path.join(out, "plan_gab.json")
json.dump(keep, open(p, "w"))
order = sorted({(r["robot"], r["job"]) for r in keep}, key=lambda x: (x[1][-2:], x[0], x[1]))
with open(os.path.join(out, "q.txt"), "w") as q:
    for robot, job in order:
        for arm in ("A", "B"):
            q.write(f"{arm} {robot} {p} {job}\n")
shutil.copy(os.path.join(src, "B.env"), os.path.join(out, "A.env"))
extra = "L9V2_PLACE_ABOVE=1\nL9V2_PLACE_TOL=1\nL9V2_PLACE_HYST=1\nL9_CSPACE_READY=1\nL9_EXEC_TABLE=1\n"
open(os.path.join(out, "B.env"), "w").write(open(os.path.join(src, "B.env")).read() + extra)
for a in ("A", "B"):
    shutil.copy(os.path.join(src, a, "HCAM_ON"), os.path.join(out, a, "HCAM_ON"))
open(os.path.join(out, "CODE"), "w").write(code + "\n")
print(dict(cnt), "jobs", len(order))
