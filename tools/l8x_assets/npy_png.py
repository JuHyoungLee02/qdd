"""Save a 2-D bool / numeric .npy as a PNG (x right, y up), Pillow.
usage: python tools/l8x_assets/npy_png.py IN.npy OUT.png"""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image


def main(argv=None):
    a = argv or sys.argv[1:]
    m = np.load(a[0]).astype(float)
    m = (255 * (m - m.min()) / max(m.max() - m.min(), 1e-9)).astype(np.uint8)
    Image.fromarray(m.T[::-1]).save(a[1])


if __name__ == "__main__":
    main()
