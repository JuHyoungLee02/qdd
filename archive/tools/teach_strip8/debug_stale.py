"""Diagnose G-stale image mismatches: for OOD-H rows, where do the rebuilt and saved v2 head images differ, and does the
TCP of the request text (NOW line) or of the row (gt.tcp) reproduce the saved image?
usage: python debug_stale.py <E-PT data dir> <out dir> [n]"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image

from harvest.astra_motion.geometry import Cam
from harvest.astra_solo.overlay import _px, head_overlay

src, out = sys.argv[1], sys.argv[2]
n_max = int(sys.argv[3]) if len(sys.argv) > 3 else 12
os.makedirs(out, exist_ok=True)
rows = [json.loads(x) for x in open(os.path.join(src, "ood_h_nd-xyz.jsonl"))]
rows = [r for r in rows if r["kind"] == "control"]
stats = []
for r in rows:
    tz = float(r["vdir"].split("_tz")[1])
    cam = Cam.from_json(json.load(open(r["cams_path"]))["head"])
    ring = np.asarray(Image.open(os.path.join(r["call_dir"], "img1_head_ring.png")).convert("RGB"))
    v2 = np.asarray(Image.open(os.path.join(r["call_dir"], "img1_head_camera.png")).convert("RGB"))
    txt = open(os.path.join(r["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
    m = re.search(r"TCP at \(([-\d.]+), ([-\d.]+), ([-\d.]+)\) m", txt)
    tcp_txt = [float(v) for v in m.groups()]
    a = np.asarray(head_overlay(ring, cam, tz, r["gt"]["tcp"])[0])[..., :3]
    b = np.asarray(head_overlay(ring, cam, tz, tcp_txt)[0])[..., :3]
    raw_diff = np.abs(ring.astype(int) - v2.astype(int)).max(-1) > 0
    da = np.abs(a.astype(int) - v2.astype(int)).max(-1) > 0
    db = np.abs(b.astype(int) - v2.astype(int)).max(-1) > 0
    ys, xs = np.nonzero(da)
    ring_px = _px(cam, np.asarray(r["gt"]["tcp"], float))
    stats.append({"id": r["id"], "n_diff_gt": int(da.sum()), "n_diff_txt": int(db.sum()),
                  "tcp_gt": [round(v, 4) for v in r["gt"]["tcp"]], "tcp_txt": tcp_txt,
                  "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None,
                  "ring_px": [round(float(v), 1) for v in ring_px] if ring_px else None,
                  "ring_vs_v2_pixels": int(raw_diff.sum())})
    if da.sum() and len([s for s in stats if s["n_diff_gt"]]) <= 3:
        Image.fromarray(np.concatenate([v2, a, (da[..., None] * 255).repeat(3, -1).astype(np.uint8)], 1)).save(
            os.path.join(out, r["id"] + "_v2_rebuilt_diff.png"))
bad = [s for s in stats if s["n_diff_gt"]]
print("N", len(stats), "bad_gt", len(bad), "bad_txt", sum(1 for s in stats if s["n_diff_txt"]))
for s in bad[:n_max]:
    print(json.dumps(s))
