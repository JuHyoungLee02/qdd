"""boost2: d-min training rows from the DAgger collection (min_format.build, L8 repeats + aux), then the aggregate
file = B-D training rows (E-DIST8 data_b1/train_d-min) + DAgger rows, and the step count that keeps B-D's passes
over the data (816 x aggregate rows / B-D rows). usage: python build_dagger.py <dagger root> <out dir>"""
import json
import os
import sys

from harvest.teach_pt import min_format as MF

root, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
c = MF.build(os.path.join(root, "train"), out, "train", "d-min", seed=0)
base = "/data/harvest/out/dist8/data_b1/train_d-min.jsonl"
nb = sum(1 for _ in open(base))
nd = sum(1 for _ in open(os.path.join(out, "train_d-min.jsonl")))
with open(os.path.join(out, "train_agg.jsonl"), "w", encoding="utf-8", newline="\n") as f:
    for p in (base, os.path.join(out, "train_d-min.jsonl")):
        for x in open(p, encoding="utf-8"):
            f.write(x)
steps = round(816 * (nb + nd) / nb)
json.dump({"dagger": c, "b1_rows": nb, "dagger_rows": nd, "steps": steps}, open(os.path.join(out, "agg.json"), "w"))
print("BUILD_DAGGER " + json.dumps({"dagger": c, "b1_rows": nb, "dagger_rows": nd, "steps": steps}))
print(f"STEPS {steps}")
