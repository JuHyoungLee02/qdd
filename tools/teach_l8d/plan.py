"""L8-D plan + job lists (prereg_l8d.md §3-4). usage:
  python plan.py <gate.json> <n_train> <out dir> <lanes> [--ood]
Writes <out>/plan_train.json (spec.plan_train over the gate's train heights), [<out>/plan_ood.json] and
<out>/jobs_<k>.txt (k = 0..lanes-1): one line per Isaac process = run_collect arguments for one (split, variant,
height) bucket, buckets dealt to lanes largest first. OOD-H: E-PT heights + the gate's outer heights, 8 standard + 8
drx seeds each (70000-); OOD-D: randx at 0.85, 40 seeds (70300-)."""
import json
import os
import sys

from harvest.teach_l8d import spec as S

gate = json.load(open(sys.argv[1]))
n, out, lanes = int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
ood = "--ood" in sys.argv
os.makedirs(out, exist_ok=True)
ws = {float(k): v for k, v in gate["ws"].items()}
train_h = [float(h) for h in gate["train_heights"]]
plan = S.plan_train(n, train_h)
json.dump(plan, open(os.path.join(out, "plan_train.json"), "w"), indent=0)
jobs = []
for (v, h), eps in S.buckets(plan).items():
    jobs.append((len(eps), f"--split train --variant {v} --table-z {h:.3f} --ws-x {ws[h][0]},{ws[h][1]} "
                           f"--plan {out}/plan_train.json --video-seeds {eps[0]['seed']},{eps[1]['seed']}"))
if ood:
    oplan, s = [], S.OOD_SETS["ood_h"].start
    for h in S.PT_OOD_H + tuple(gate["outer_ood_heights"]):
        h = round(float(h), 3)
        wsx = ws.get(h)
        if wsx is None:  # an E-PT height outside the gate range is not generated (recorded in the counts)
            continue
        for v in ("standard", "drx"):
            for _ in range(8):
                oplan.append({"seed": s, "split": "ood_h", "task": S.task_of(s), "variant": v, "table_z": h})
                s += 1
    for i in range(40):
        s = S.OOD_SETS["ood_d"].start + i
        oplan.append({"seed": s, "split": "ood_d", "task": S.task_of(s), "variant": "randx", "table_z": 0.85})
    json.dump(oplan, open(os.path.join(out, "plan_ood.json"), "w"), indent=0)
    b = {}
    for e in oplan:
        b.setdefault((e["split"], e["variant"], e["table_z"]), []).append(e)
    for (sp, v, h), eps in b.items():
        jobs.append((len(eps), f"--split {sp} --variant {v} --table-z {h:.3f} --ws-x {ws[h][0]},{ws[h][1]} "
                               f"--plan {out}/plan_ood.json --confirm-ood"))
jobs.sort(key=lambda j: -j[0])
load = [0] * lanes
files = [open(os.path.join(out, f"jobs_{k}.txt"), "w") for k in range(lanes)]
for c, j in jobs:
    k = load.index(min(load))
    load[k] += c
    files[k].write(j + "\n")
for f in files:
    f.close()
print(json.dumps({"train": len(plan), "buckets": len(jobs), "lane_load": load, "train_heights": train_h}))
