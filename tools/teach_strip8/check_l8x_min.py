"""L8D's L8-X eval s-min rows must equal strip.minimal(prompt_v2.txt) of the same call, with the ring-only head image.
usage: python check_l8x_min.py <eval dir> <set> [...]"""
import json
import os
import sys

from harvest.teach_strip8 import strip as S

d = sys.argv[1]
for s in sys.argv[2:]:
    n = ok = img = 0
    for x in open(os.path.join(d, f"{s}_s-min.jsonl")):
        r = json.loads(x)
        if r["kind"] != "control":
            continue
        n += 1
        v2 = open(os.path.join(r["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
        ok += open(r["prompt_path"], encoding="utf-8").read() == S.minimal(v2)
        img += os.path.basename(r["images"][0]) == "img1_head_ring.png"
    print(json.dumps({"set": s, "n": n, "text_equal": ok, "ring_image": img}))
