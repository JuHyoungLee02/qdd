"""Eye-check sheet of one episode: the head image (with overlay) and right wrist image Astra received at each call
site (first attempt), up to --n sites, with the command written under each pair.
usage: python tools/astra_solo/sheet.py <episode dir> <out.jpg> [--n 8]"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=8)
    a = ap.parse_args()
    res = json.load(open(os.path.join(a.ep, "result.json")))
    sites = [c for c in res["calls"] if c["attempt"] == 0][: a.n]
    tiles = []
    for c in sites:
        d = os.path.join(a.ep, "calls", f"c{c['call']:03d}")
        h = Image.open(os.path.join(d, "img1_head_camera.png")).convert("RGB")
        w = Image.open(os.path.join(d, "img2_right_wrist_camera.png")).convert("RGB")
        w = w.resize((int(w.width * h.height / w.height), h.height))
        t = Image.new("RGB", (h.width + w.width, h.height + 30), (0, 0, 0))
        t.paste(h, (0, 0))
        t.paste(w, (h.width, 0))
        cmd = ((c.get("parsed") or {}).get("command")) or {"mode": "invalid"}
        txt = f"site {c['site']} {json.dumps(cmd)[:150]}"
        ImageDraw.Draw(t).text((4, h.height + 8), txt, fill=(255, 255, 0))
        tiles.append(t)
    if not tiles:
        return
    cols = 2
    W, H = tiles[0].width, tiles[0].height
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols, H * rows), (40, 40, 40))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * W, (i // cols) * H))
    sheet.thumbnail((2200, 2200))
    sheet.save(a.out, quality=85)


if __name__ == "__main__":
    main()
