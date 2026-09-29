"""Eye check (P77 / P82: draw on sample frames before trusting an overlay): the production coupling overlay drawn on
R-set head images for the frame test (run_dyn.r_head_overlay) and on G-set images (run_dyn.g_couple_images), tiled
into one JPEG. usage (pod): python tools/prompt_health/overlay_sheet.py --out sheet.jpg [--n 6]"""
from __future__ import annotations

import argparse
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_dyn as RD  # noqa: E402


def main(argv=None):
    from PIL import Image
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=6)
    a = ap.parse_args(argv)
    tiles = []
    for r in RD.frame_rows(RD.r_rows(), 60)[:a.n]:
        tiles.append(Image.open(io.BytesIO(RD.r_head_overlay(r))).convert("RGB"))
    for key, sd, meta in RD.g_snaps()[:2]:
        ims = RD.g_couple_images(sd, meta)
        tiles.append(Image.open(io.BytesIO(ims["cam_head"])).convert("RGB"))
        tiles.append(Image.open(io.BytesIO(ims["cam_wrist_right"])).convert("RGB").resize((672, 376)))
    W, H, cols = 672, 376, 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols, H * rows))
    for i, t in enumerate(tiles):
        sheet.paste(t.resize((W, H)), ((i % cols) * W, (i // cols) * H))
    sheet = sheet.resize((W * cols // 2, H * rows // 2))
    sheet.save(a.out, quality=85)
    print("SHEET", a.out, len(tiles), np.asarray(sheet).shape)


if __name__ == "__main__":
    main()
