"""D round 2 Mbc training file: B+obj-D rows (E-DIST8 data_open/train_b_obj_d.jsonl, unchanged) + confusing-distractor
d-min rows (L8D conf1) + RefSpatial pointing rows at 15 % of the final file; steps = 1,088 x rows / B+obj rows.
usage: python build_mbc.py <conf1 d-min rows jsonl> <refsp pool jsonl> <out dir>"""
import json
import os
import sys

base = "/data/harvest/out/dist8/data_open/train_b_obj_d.jsonl"
conf, pool, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
nb = sum(1 for _ in open(base))
nc = sum(1 for _ in open(conf))
nr = round(0.15 / 0.85 * (nb + nc))
pr = [x for _, x in zip(range(nr), open(pool))]
if len(pr) < nr:
    raise SystemExit(f"pool has {len(pr)} rows, need {nr}")
with open(os.path.join(out, "train_mbc.jsonl"), "w", encoding="utf-8", newline="\n") as f:
    for p in (base, conf):
        for x in open(p, encoding="utf-8"):
            f.write(x)
    for x in pr:
        f.write(x)
steps = round(1088 * (nb + nc + nr) / nb)
info = {"b_obj_rows": nb, "conf_rows": nc, "refsp_rows": nr, "refsp_share": round(nr / (nb + nc + nr), 4), "steps": steps}
json.dump(info, open(os.path.join(out, "mbc.json"), "w"))
print("BUILD_MBC " + json.dumps(info))
print(f"STEPS {steps}")
