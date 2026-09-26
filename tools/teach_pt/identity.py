"""E-PT gate G1 (prereg_pt.md §2): are the E-PT collection's states the E-TEACH-L8 states? For every call of every
episode under <pt root>/<split>/<variant>/, compare prompt_v2.txt (the v2 request E-PT rebuilt) with the L8
collection's prompt.txt byte for byte, and the two v2 head PNGs by pixel, and the label rows (step, gt tcp).
usage: python identity.py <pt collect root> <l8 collect root> <split>
prints IDENTITY {...}: calls compared, identical text / image / label shares, first differences."""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

pt, l8, split = sys.argv[1], sys.argv[2], sys.argv[3]
n = same_t = same_i = same_l = 0
missing, diffs = [], []
for ep in sorted(glob.glob(os.path.join(pt, split, "*", "*"))):
    rel = os.path.relpath(ep, pt)
    other = os.path.join(l8, rel)
    if not os.path.isdir(other):
        missing.append(rel)
        continue
    la = {json.loads(x)["call"]: json.loads(x) for x in open(os.path.join(ep, "labels.jsonl"))}
    lb = {json.loads(x)["call"]: json.loads(x) for x in open(os.path.join(other, "labels.jsonl"))}
    for c in sorted(la):
        d1, d2 = os.path.join(ep, "calls", f"c{c:03d}"), os.path.join(other, "calls", f"c{c:03d}")
        if not os.path.exists(os.path.join(d2, "prompt.txt")):
            diffs.append((rel, c, "missing_in_l8"))
            continue
        n += 1
        t = open(os.path.join(d1, "prompt_v2.txt"), "rb").read() == open(os.path.join(d2, "prompt.txt"), "rb").read()
        a = np.asarray(Image.open(os.path.join(d1, "img1_head_camera.png")), np.int16)
        b = np.asarray(Image.open(os.path.join(d2, "img1_head_camera.png")), np.int16)
        i = a.shape == b.shape and int(np.abs(a - b).max()) == 0
        lab = c in lb and la[c]["step"] == lb[c]["step"] and la[c]["gt"]["tcp"] == lb[c]["gt"]["tcp"]
        same_t, same_i, same_l = same_t + t, same_i + i, same_l + lab
        if not (t and i and lab) and len(diffs) < 10:
            diffs.append((rel, c, {"text": t, "image": i, "label": lab,
                                   "img_maxdiff": None if a.shape != b.shape else int(np.abs(a - b).max())}))
    if len(lb) != len(la):
        diffs.append((rel, "n_calls", len(la), len(lb)))
print("IDENTITY " + json.dumps({"calls": n, "text_same": same_t, "image_same": same_i, "label_same": same_l,
                                "missing_episodes": missing[:10], "n_missing": len(missing), "first_diffs": diffs[:10]}))
