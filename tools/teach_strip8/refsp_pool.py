"""Build the RefSpatial Simulator pointing pool: records shuffled (seed 0), at most one row per record, up to N rows.
usage: python refsp_pool.py <root> <N>  -> <root>/pool.jsonl"""
import json
import os
import sys

import numpy as np
from PIL import Image

from harvest.teach_strip8.refsp import rows_of

root, n = sys.argv[1], int(sys.argv[2])
img_dir = os.path.join(root, "Simulator", "image", "RefSpatial", "Simulator", "image")
m = json.load(open(os.path.join(root, "Simulator", "metadata.json")))
order = np.random.default_rng(0).permutation(len(m))
rng = np.random.default_rng(1)
out, size = [], {}
for i in order:
    rec = m[int(i)]
    p = os.path.join(img_dir, rec["image"][0])
    if not os.path.exists(p):
        continue
    W, H = Image.open(p).size
    rows = rows_of(rec, img_dir, W, H)
    if rows:
        out.append(rows[int(rng.integers(len(rows)))])
    if len(out) >= n:
        break
with open(os.path.join(root, "pool.jsonl"), "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
print("POOL", len(out))
