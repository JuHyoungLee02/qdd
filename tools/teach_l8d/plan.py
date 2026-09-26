"""L8-D / L8-X plan + job lists (prereg_l8d.md §3-4 and change 2). usage:
  python plan.py <gate.json> <n_train> <out dir> <lanes> [--ood] [--x] [--pod <dir the job lines point to>]
Phase 1 (default): <out>/plan_train.json (spec.plan_train over the gate's train heights), [<out>/plan_ood.json]
  OOD-H: E-PT heights + the gate's outer heights, 8 standard + 8 drx seeds each (70000-); OOD-D: randx at 0.85, 40
  seeds (70300-).
--x (L8-X tasks, objset "x"): <out>/plan_x.json (spec.plan_x from seed 31200), [<out>/plan_ood_x.json] OOD-O: the
  small-cup task (unseen object) 40 seeds (70100-), OOD-T: the two held-out compositions 20 seeds each (70700-), over
  the train heights round-robin, standard / drx alternating.
<out>/jobs_<k>.txt (k = 0..lanes-1): one line per Isaac process = run_collect arguments for one (split, variant,
height) bucket, buckets dealt to lanes largest first."""
import json
import os
import sys

from harvest.teach_l8d import spec as S

gate = json.load(open(sys.argv[1]))
n, out, lanes = int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
ood, xmode = "--ood" in sys.argv, "--x" in sys.argv
pod = sys.argv[sys.argv.index("--pod") + 1] if "--pod" in sys.argv else out
os.makedirs(out, exist_ok=True)
ws = {round(float(k), 3): v for k, v in gate["ws"].items()}
train_h = [float(h) for h in gate["train_heights"]]
extra = " --objset x" if xmode else ""
name = "plan_x.json" if xmode else "plan_train.json"
plan = S.plan_x(n, train_h) if xmode else S.plan_train(n, train_h)
json.dump(plan, open(os.path.join(out, name), "w"), indent=0)
jobs = []
for (v, h), eps in S.buckets(plan).items():
    jobs.append((len(eps), f"--split train --variant {v} --table-z {h:.3f} --ws-x {ws[h][0]},{ws[h][1]} "
                           f"--plan {pod}/{name} --video-seeds {eps[0]['seed']},{eps[1]['seed']}{extra}"))
if ood:
    oplan = []
    if not xmode:
        s = S.OOD_SETS["ood_h"].start
        for h in S.PT_OOD_H + tuple(gate["outer_ood_heights"]):
            h = round(float(h), 3)
            if ws.get(h) is None:  # an E-PT height outside the gate range is not generated (recorded in the counts)
                continue
            for v in ("standard", "drx"):
                for _ in range(8):
                    oplan.append({"seed": s, "split": "ood_h", "task": S.task_of(s), "variant": v, "table_z": h})
                    s += 1
        for i in range(40):
            s = S.OOD_SETS["ood_d"].start + i
            oplan.append({"seed": s, "split": "ood_d", "task": S.task_of(s), "variant": "randx", "table_z": 0.85})
    else:
        sets = [("ood_o", t, 40) for t in S.OOD_O_TASKS] + [("ood_t", t, 20) for t in S.OOD_T_TASKS]
        nxt = {k: S.OOD_SETS[k].start for k in ("ood_o", "ood_t")}
        for sp, t, m in sets:
            for i in range(m):
                s = nxt[sp]
                nxt[sp] += 1
                oplan.append({"seed": s, "split": sp, "task": t, "variant": ("standard", "drx")[i % 2],
                              "table_z": train_h[i % len(train_h)], "objset": "x"})
    oname = "plan_ood_x.json" if xmode else "plan_ood.json"
    json.dump(oplan, open(os.path.join(out, oname), "w"), indent=0)
    b = {}
    for e in oplan:
        b.setdefault((e["split"], e["variant"], e["table_z"]), []).append(e)
    for (sp, v, h), eps in b.items():
        jobs.append((len(eps), f"--split {sp} --variant {v} --table-z {h:.3f} --ws-x {ws[h][0]},{ws[h][1]} "
                               f"--plan {pod}/{oname} --confirm-ood{extra}"))
jobs.sort(key=lambda j: -j[0])
load = [0] * lanes
files = [open(os.path.join(out, f"jobs_{k}.txt"), "w", newline="\n") for k in range(lanes)]
for c, j in jobs:
    k = load.index(min(load))
    load[k] += c
    files[k].write(j + "\n")
for f in files:
    f.close()
print(json.dumps({"train": len(plan), "buckets": len(jobs), "lane_load": load, "train_heights": train_h}))
