"""Pre-registered top-up (l9v2_general_ab.md "Rows and seeds"): append the next rows of the SAME selection for robots
whose arm has < 20 rendered episodes. Rows come from a fresh selection with a larger n (deterministic order), minus the
rows already in the plan; jobs of 5 rows per (arm, ext_p, hcam) group named gab_<robot>_X<side><k>; both arms queued.
usage: python3 add_rows.py <ab dir> <code dir> <extra rows> robot=spec [robot=spec ...]   (spec as gab_select.py)"""
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict

ab, code, extra = sys.argv[1], sys.argv[2], int(sys.argv[3])
specs = sys.argv[4:]
p = os.path.join(ab, "plan_gab.json")
plan = json.load(open(p))
have = {int(r["seed"]) for r in plan}
tmp = tempfile.mkdtemp()
per_robot = {}
for spec in specs:
    robot = spec.split("=", 1)[0]
    n_have = sum(1 for r in plan if r["robot"] == robot)
    subprocess.run([sys.executable, os.path.join(code, "tools/l9/gab/gab_select.py"), tmp, str(n_have + extra), spec],
                   check=True, stdout=subprocess.DEVNULL, env=dict(os.environ, GAB_ROWS_PER_JOB="5"))
    sel = [r for r in json.load(open(os.path.join(tmp, "plan_gab.json"))) if int(r["seed"]) not in have]
    per_robot[robot] = sel[:extra]
new_q = []
for robot, rows in per_robot.items():
    cnt = defaultdict(int)
    for r in rows:
        side = (r.get("arm") or "x")[0] + ("" if r.get("ext_p") is None else f"e{round(float(r['ext_p']) * 10)}") \
            + (str(r["hcam"])[:2] if r.get("hcam") else "")
        r["job"] = f"gab_{robot}_X{side}{cnt[side] // 5:02d}"
        cnt[side] += 1
        plan.append(r)
    for job in sorted({r["job"] for r in rows}):
        for arm in ("A", "B"):
            new_q.append(f"{arm} {robot} {p} {job}\n")
    print(robot, "added rows", len(rows), "jobs", len({r['job'] for r in rows}))
json.dump(plan, open(p + ".tmp", "w"))
os.replace(p + ".tmp", p)
with open(os.path.join(ab, "q.txt"), "a") as f:
    f.writelines(new_q)
with open(os.path.join(ab, "rows.tsv"), "a") as t:
    for rows in per_robot.values():
        for r in rows:
            t.write("\t".join(str(x) for x in (r["job"], r["robot"], r.get("def"), r.get("task_family"), r.get("arm"),
                                               r["seed"])) + "\n")
