"""E-STRIP8 gate G-stale (prereg_strip8.md §2): the s-stale rebuild with the row's TRUE table height must reproduce the
saved v2 request of OOD-H (text byte-identical, head image pixel-identical) -- then the only difference of the s-stale
arm is the hand-written height. usage: python check_stale.py <E-PT data dir> <scratch dir> [max rows]"""
import json
import os
import sys

import numpy as np
from PIL import Image

from harvest.teach_strip8.dataset import stale_request

src, tmp = sys.argv[1], sys.argv[2]
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
os.makedirs(tmp, exist_ok=True)
rows = [json.loads(x) for x in open(os.path.join(src, "ood_h_nd-xyz.jsonl"))]
rows = [r for r in rows if r["kind"] == "control"][:cap]
n = same_t = same_i = 0
bad = []
for r in rows:
    tz = float(r["vdir"].split("_tz")[1])
    v2 = open(os.path.join(r["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
    png = os.path.join(tmp, r["id"] + ".png")
    t = stale_request(r, v2, tz, png)
    a = np.asarray(Image.open(png).convert("RGB"))
    b = np.asarray(Image.open(os.path.join(r["call_dir"], "img1_head_camera.png")).convert("RGB"))
    n += 1
    same_t += t == v2
    same_i += bool(np.array_equal(a, b))
    if t != v2 or not np.array_equal(a, b):
        bad.append({"id": r["id"], "text": t == v2, "max_abs": int(np.abs(a.astype(int) - b.astype(int)).max())})
    os.remove(png)
out = {"n": n, "text_identical": same_t, "image_identical": same_i,
       "pass": n > 0 and same_t / n >= 0.99 and same_i / n >= 0.99, "bad": bad[:10]}
print("G_STALE " + json.dumps(out))
