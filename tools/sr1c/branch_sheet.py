"""E-SR1c prerequisite check by eye (P81 / user-log 95): head frames of random far snapshots with the recorded chunk
path (white) and the accepted branch paths (one colour per forced direction, dot at the end) projected with the sim
head camera (r2_ma2.project_head). Path = measured finger midpoint at the snapshot + FK displacement of the targets.
  python tools/sr1c/branch_sheet.py --branches DIR --n 12 --out sheet.jpg
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

COL = {"plus_x": (255, 80, 80), "plus_x_plus_y": (255, 170, 0), "plus_y": (230, 230, 0), "minus_x_plus_y": (0, 200, 0),
       "minus_x": (0, 220, 220), "minus_x_minus_y": (60, 120, 255), "minus_y": (170, 80, 255),
       "plus_x_minus_y": (255, 80, 200)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--branches", required=True)
    ap.add_argument("--view", default="/data/harvest/data/ma2/view")
    ap.add_argument("--r2", default="/data/harvest/r2/train")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from PIL import Image, ImageDraw

    from harvest.train import sr1c_branch as B
    from harvest.train.r2_ma2 import project_head
    from harvest.train.se2e_data import load_arm_chain
    chain = load_arm_chain("/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf", "right")
    by = {}
    for p in sorted(glob.glob(os.path.join(a.branches, "*.jsonl"))):
        for x in open(p, encoding="utf-8"):
            r = json.loads(x)
            by.setdefault((r["variant"], r["task"], r["kind"], r["seed"], r["k"]), []).append(r)
    keys = sorted(by)
    pick = [keys[i] for i in np.random.default_rng(a.seed).choice(len(keys), size=min(a.n, len(keys)), replace=False)]
    tiles = []
    for (v, t, kd, seed, k) in pick:
        img = Image.open(os.path.join(a.view, v, t, kd, "img", f"ep{seed}", f"f{k:04d}_cam_head.jpg")).convert("RGB")
        z = np.load(os.path.join(a.r2, v, t, kd, f"ep{seed}.npz"))
        tcp = np.asarray(z["tcp"][k], float)
        d = ImageDraw.Draw(img)
        rows = by[(v, t, kd, seed, k)]
        paths = []
        src = None
        for x in open(os.path.join(a.view, v, t, f"{kd}.stageb.jsonl"), encoding="utf-8"):
            r = json.loads(x)
            if r["seed"] == seed and r["k"] == k:
                src = r
                break
        if src is not None:
            P, _ = B.fk_pose(chain, np.asarray(src["action_exec"], float)[:, :7])
            paths.append(((255, 255, 255), tcp + (P - P[0])))
        for r in rows:
            P, _ = B.fk_pose(chain, np.asarray(r["action_exec"], float)[:, :7])
            paths.append((COL[r["committed"]["dir_xy"]], tcp + (P - P[0])))
        for col, path in paths:
            uv = project_head(path)
            d.line([tuple(p) for p in uv], fill=col, width=3)
            e = uv[-1]
            d.ellipse([e[0] - 4, e[1] - 4, e[0] + 4, e[1] + 4], fill=col)
        d.text((6, 6), f"{v}/{t}/{kd} ep{seed} k{k} {src['phase_id'] if src else ''}", fill=(255, 255, 255))
        tiles.append(img)
    W, H = tiles[0].size
    cols = 3
    sheet = Image.new("RGB", (W * cols, H * ((len(tiles) + cols - 1) // cols)), (0, 0, 0))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * W, (i // cols) * H))
    sheet.save(a.out, quality=85)
    print(json.dumps({"out": a.out, "n": len(tiles), "picked": [list(p) for p in pick]}), flush=True)


if __name__ == "__main__":
    main()
