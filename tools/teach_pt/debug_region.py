"""E-PT debug: draw the resolver's region (red), seed (green) and top band (yellow) on a call's head image.
usage: python debug_region.py <call dir> <x0..1000> <y0..1000> <out.png> [table_z]"""
import json
import os
import sys

import numpy as np
from PIL import Image

from harvest.astra_motion import geometry as G
from harvest.astra_solo import resolve as RS

d, x, y, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
tz = float(sys.argv[5]) if len(sys.argv) > 5 else 0.85
cam = G.Cam.from_json(json.load(open(os.path.join(d, "cams.json")))["head"])
depth = np.load(os.path.join(d, "head_depth.npz"))["depth"]
img = np.asarray(Image.open(os.path.join(d, "img1_head_camera.png")).convert("RGB")).copy()
P = RS.depth_points(cam, depth)
plane = RS.table_plane(P, tz)
hgt = P[..., 2] - plane
above = np.isfinite(hgt) & (hgt > RS.H_MIN)
iu, iv = RS.to_pixel([x, y], cam.W, cam.H)
reg = RS._region(P, above, (iv, iu)) if above[iv, iu] else np.zeros_like(above)
img[above & ~reg] = (img[above & ~reg] * 0.5 + np.array([0, 0, 120])).astype(np.uint8)
img[reg] = (img[reg] * 0.4 + np.array([150, 0, 0])).astype(np.uint8)
if reg.any():
    t = np.percentile(hgt[reg], 95)
    band = reg & (hgt >= t - RS.TOP_BAND_M)
    img[band] = (255, 255, 0)
img[max(0, iv - 3):iv + 4, max(0, iu - 3):iu + 4] = (0, 255, 0)
Image.fromarray(img).save(out)
print(json.dumps(RS.resolve_point(cam, depth, tz, [x, y])))
