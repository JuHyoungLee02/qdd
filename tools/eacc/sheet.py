"""E-ACC bench eye-check sheet (prereg §2.3, P77/P82): per snapshot the v2 head image (production overlay drawn as
sent) and the right wrist image, plus -- for the eye check only, never sent to a model -- the oracle subgoal at
arrival (red cross) and the stand-in policy's wrong goal (magenta cross) projected into the head image.
usage: python tools/eacc/sheet.py --bench B --out sheet.jpg [--ids a,b]"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms as A  # noqa: E402
import bench as B  # noqa: E402
import run_eacc as R  # noqa: E402


def tile(sd: str, meta: dict, arm: str = "v2"):
    from PIL import Image, ImageDraw

    from harvest.couple.overlay import _px
    imgs, _, models, _ = A.images(sd, meta, A.parse_arm(arm))
    head = Image.open(io.BytesIO(imgs["cam_head"])).convert("RGB")
    wrist = Image.open(io.BytesIO(imgs["cam_wrist_right"])).convert("RGB")
    d = ImageDraw.Draw(head)
    o = B.oracle(meta)
    ra = B.at(meta["path"], meta["t_snap"] + B.L_ARR)
    marks = []
    if o["dir_arr"] is not None:
        marks.append((np.asarray(ra["tip"]) + np.asarray(o["dir_arr"]), (255, 0, 0)))
        marks.append((np.asarray(ra["tip"]), (255, 255, 255)))
    if meta.get("wrong_goal"):
        marks.append((np.asarray(meta["wrong_goal"]), (255, 0, 255)))
    for p, col in marks:
        q = _px(models["cam_head"], p)
        if q is not None:
            d.line([q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6], fill=col, width=2)
            d.line([q[0] - 6, q[1] + 6, q[0] + 6, q[1] - 6], fill=col, width=2)
    w = wrist.resize((int(wrist.width * head.height / wrist.height), head.height))
    out = Image.new("RGB", (head.width + w.width, head.height + 18), (0, 0, 0))
    out.paste(head, (0, 18))
    out.paste(w, (head.width, 18))
    ImageDraw.Draw(out).text((4, 3), f"{meta['id']} {meta['task']} snap={o['phase_send']} arr={o['phase_arr']} "
                                     f"exp={o['expected']} seg={o['segments']}", fill=(255, 255, 0))
    return out


def main(argv=None):
    from PIL import Image
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default="")
    ap.add_argument("--arm", default="v2")
    a = ap.parse_args(argv)
    snaps = R.load_bench(a.bench)
    if a.ids:
        keep = set(a.ids.split(","))
        snaps = [s for s in snaps if s[0] in keep]
    tiles = [tile(sd, m, a.arm) for _, sd, m in snaps]
    if not tiles:
        raise SystemExit("no snapshots")
    cols = 2
    W, H = max(t.width for t in tiles), max(t.height for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols, H * rows), (40, 40, 40))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * W, (i // cols) * H))
    sheet.save(a.out, quality=85)
    print(json.dumps({"tiles": len(tiles), "size": sheet.size}))


if __name__ == "__main__":
    main()
