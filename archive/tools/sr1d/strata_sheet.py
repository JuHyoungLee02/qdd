"""E-SR1d G-a eye check (docs/stage3/prereg_sr1d.md §0.5): random loaded VAL snapshots of one stratum (authority
proxy), head frame + active wrist frame side by side with the key, d and gripper state; seeded, no model output.
  python tools/sr1d/strata_sheet.py --meta META --img-root /data/harvest/data/se2e_c1/conv --stratum far --n 16 \
      --seed 0 --out sheet.jpg
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--rows", default="/data/harvest/data/se2e_c1/conv")
    ap.add_argument("--img-root", default="/data/harvest/data/se2e_c1/conv")
    ap.add_argument("--stratum", default="far")
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from PIL import Image, ImageDraw

    from harvest.train.se2e_data import needed_cams
    ms = [json.loads(x) for x in open(a.meta, encoding="utf-8")]
    pool = [m for m in ms if m["split"] == "val" and m["stratum"] == a.stratum
            and set(needed_cams(m)) <= set(m["has_cams"])]
    pick = random.Random(a.seed).sample(pool, min(a.n, len(pool)))
    want = {m["key"] for m in pick}
    imgs = {}
    for kind in ("RB1", "RB2"):
        for x in open(os.path.join(a.rows, f"{kind}.stageb.jsonl"), encoding="utf-8"):
            r = json.loads(x)
            key = f"{r['kind']}_ep{r['seed']}_k{r['k']}"
            if key in want:
                imgs[key] = r["images"]
    W, Hh = 672 + 424, 376
    sheet = Image.new("RGB", (W * 2, Hh * ((len(pick) + 1) // 2)), "white")
    for i, m in enumerate(pick):
        im = imgs[m["key"]]
        head = Image.open(os.path.join(a.img_root, im["cam_head"])).convert("RGB").resize((672, 376))
        wr = Image.open(os.path.join(a.img_root, im[f"cam_wrist_{m['arm']}"])).convert("RGB")
        wr.thumbnail((424, 376))
        tile = Image.new("RGB", (W, Hh), "black")
        tile.paste(head, (0, 0))
        tile.paste(wr, (672, 0))
        dr = ImageDraw.Draw(tile)
        txt = f"{i} {m['key']} {m['arm']} d={m['d']} hold={m['holding']} {m['stratum']}"
        dr.rectangle([0, 0, 520, 18], fill="black")
        dr.text((4, 3), txt, fill=(255, 255, 0))
        sheet.paste(tile, ((i % 2) * W, (i // 2) * Hh))
    sheet.save(a.out, quality=80)
    print(json.dumps({"n": len(pick), "pool": len(pool), "keys": [m["key"] for m in pick]}))


if __name__ == "__main__":
    main()
