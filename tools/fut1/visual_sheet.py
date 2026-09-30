"""E-FUT1 data gate, visual part (prereg_fut1.md §7): 20 random held-out delta > 0 sites -> one contact sheet.
Per site: head ring 'cur' (ring = TCP now) | head ring 'roll' (ring = in-flight goal) | wrist (now) | head at delta 0
(arrival), and under it the TCP line of cur / roll and the provisional history line. A person checks: the cur ring on
the gripper, the roll ring where the delta-0 image shows the gripper, the wrist view of the same moment.
  python tools/fut1/visual_sheet.py --data /data/harvest/out/fut1/data --out /data/harvest/out/fut1/data/visual_check.png"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
from PIL import Image, ImageDraw


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args(argv)
    cur = [json.loads(x) for x in open(os.path.join(a.data, "eval_cur.jsonl"))]
    roll = {r["id"][:-4]: r for r in map(json.loads, open(os.path.join(a.data, "eval_roll.jsonl")))}
    pos = [r for r in cur if r["delta"] > 0]
    rng = np.random.default_rng(7)
    pick = [pos[i] for i in rng.choice(len(pos), size=min(a.n, len(pos)), replace=False)]
    W, H, TH = 336, 188, 64
    sheet = Image.new("RGB", (W * 4, (H + TH) * len(pick)), "white")
    dr = ImageDraw.Draw(sheet)
    for k, r in enumerate(pick):
        rr = roll[r["id"][:-3]]
        d0 = r["images"][0].replace(f"_d{r['delta']}_ring_cur", "_d0.0_ring_cur")
        ims = [r["images"][0], rr["images"][0], r["images"][1], d0]
        y = k * (H + TH)
        for j, p in enumerate(ims):
            if os.path.exists(p):
                sheet.paste(Image.open(p).convert("RGB").resize((W, H)), (j * W, y))
        tc = [x for x in open(r["prompt_path"], encoding="utf-8").read().splitlines() if x.startswith("- TCP at (")]
        tr = [x for x in open(rr["prompt_path"], encoding="utf-8").read().splitlines() if x.startswith("- TCP at (")]
        hist = [x for x in open(r["prompt_path"], encoding="utf-8").read().splitlines() if "(error 0 mm)" in x]
        txt = (f"{r['id']}  delta {r['delta']} s  moving {r['moving_mm']} mm  step {r['step']}\n"
               f"cur {tc[0] if tc else '?'} | roll {tr[0] if tr else '?'}\n{(hist[-1] if hist else 'NO provisional line')[:220]}")
        dr.text((4, y + H + 2), txt, fill="black")
    sheet.save(a.out)
    print(a.out, len(pick))


if __name__ == "__main__":
    main()
