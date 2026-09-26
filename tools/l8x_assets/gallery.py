"""Tile every <kind>_s<seed>/head_overlay.png of a validation run into one gallery image (pure, Pillow).
usage: python tools/l8x_assets/gallery.py RUN_DIR OUT.png [--seed 0 (-1 = every dir)] [--cols 4]"""
from __future__ import annotations

import argparse
import os

from PIL import Image


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args(argv)
    dirs = sorted(d for d in os.listdir(a.run) if (a.seed < 0 or d.endswith(f"_s{a.seed}"))
                  and os.path.exists(os.path.join(a.run, d, "head_overlay.png")))
    ims = [Image.open(os.path.join(a.run, d, "head_overlay.png")).convert("RGB").resize((336, 188)) for d in dirs]
    rows = (len(ims) + a.cols - 1) // a.cols
    g = Image.new("RGB", (336 * a.cols, 188 * rows))
    for i, im in enumerate(ims):
        g.paste(im, (336 * (i % a.cols), 188 * (i // a.cols)))
    g.save(a.out)
    print(len(ims), "tiles ->", a.out)


if __name__ == "__main__":
    main()
