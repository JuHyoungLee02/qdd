"""Grid-free check for a training JSONL: every image must be a grid-free original — L8-X head images only as the ring
image (img1_head_ring.png: TCP ring, no table grid) and the wrist camera, open-data frames as they are; the grid overlay
head image (img1_head_camera.png, drawn grid) must not appear, and no request text may mention the grid.
Prints counts as JSON; exit 1 when any grid image or grid text is found. usage: python grid_check.py <jsonl>"""
import collections
import json
import os
import sys

kinds, grid_img, grid_txt, n = collections.Counter(), 0, 0, 0
for line in open(sys.argv[1]):
    r = json.loads(line)
    n += 1
    for p in r["images"]:
        b = os.path.basename(p)
        kinds["l8x_ring" if b == "img1_head_ring.png" else "l8x_wrist" if b == "img2_right_wrist_camera.png"
              else "l8x_grid_head" if b == "img1_head_camera.png" else "open_frame"] += 1
        grid_img += b == "img1_head_camera.png"
    t = r.get("prompt") if r.get("kind") != "control" else open(r["prompt_path"], encoding="utf-8").read()
    grid_txt += "grid" in (t or "").lower()
print(json.dumps({"rows": n, "images": dict(kinds), "grid_images": grid_img, "rows_mentioning_grid": grid_txt}))
sys.exit(1 if grid_img or grid_txt else 0)
