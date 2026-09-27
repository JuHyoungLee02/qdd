"""G-px arm of E-PRIV8 (prereg_priv8.md change 1): the E-DIST8 D (point) rows with a PIXEL-coordinate grid drawn on
the head image -- thin white lines every 100 on the 0-1000 scale of point_2d (x from the left, y from the top), labels
on the top and left edges. Image-plane only: no table height or any scene truth goes into it (user-log 154). The
request legend describes the grid; labels, answers, order and aux rows are otherwise unchanged; comparison arm =
E-DIST8 B-D (the same rows without the grid)."""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np

from ..astra_solo import nd_prompts as NP

STEP = 100
_RING_ND = "- White ring with a black outline: the TCP now. Nothing else is drawn; the wrist image has no drawing.\n"
LEGEND = ("- Thin white lines with numbers on the top and left edges: image coordinates every 100 on the 0-1000 scale "
          "of point_2d (x from the left edge, y from the top edge); drawn on the image, not on the table.\n")
_RING_GPX = "- White ring with a black outline: the TCP now.\n" + LEGEND + "- The wrist image has no drawing.\n"
AUX_LEGEND = ("Thin white lines on image 1 mark image coordinates every 100 on a 0-1000 scale (labels on the top and "
              "left edges).\n")
assert _RING_ND in NP._OVL_ND


def px_grid(img: np.ndarray) -> np.ndarray:
    from PIL import Image, ImageDraw
    base = Image.fromarray(np.ascontiguousarray(img)[..., :3]).convert("RGBA")
    W, H = base.size
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for v in range(STEP, 1000, STEP):
        x, y = round(v / 1000 * W), round(v / 1000 * H)
        d.line([(x, 0), (x, H - 1)], fill=(255, 255, 255, 110), width=1)
        d.line([(0, y), (W - 1, y)], fill=(255, 255, 255, 110), width=1)
    out = Image.alpha_composite(base, layer)
    dt = ImageDraw.Draw(out)
    for v in range(STEP, 1000, STEP):
        x, y = round(v / 1000 * W), round(v / 1000 * H)
        dt.text((x + 2, 1), str(v), fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        dt.text((2, y + 1), str(v), fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    return np.asarray(out.convert("RGB"))


def gpx_text(t: str) -> str:
    if LEGEND in t:
        return t
    if t.count(_RING_ND) != 1:
        raise ValueError("gpx_text: no ring-only legend")
    return t.replace(_RING_ND, _RING_GPX)


def gpx_aux(t: str) -> str:
    return t if AUX_LEGEND in t else AUX_LEGEND + t


def build(src: str, out_dir: str, name: str) -> dict:
    from PIL import Image
    rows = [json.loads(x) for x in open(src, encoding="utf-8")]
    idir, pdir = os.path.join(out_dir, "gpx_img"), os.path.join(out_dir, "prompts", name)
    os.makedirs(idir, exist_ok=True)
    os.makedirs(pdir, exist_ok=True)
    drawn: dict = {}
    out, seen = [], {}

    def head(p):
        if p not in drawn:
            q = os.path.join(idir, hashlib.sha1(p.encode()).hexdigest()[:16] + ".png")
            if not os.path.exists(q):
                Image.fromarray(px_grid(np.asarray(Image.open(p).convert("RGB")))).save(q)
            drawn[p] = q
        return drawn[p]

    for r in rows:
        ims = [head(r["images"][0])] + list(r["images"][1:])
        if r["kind"] == "aux":
            out.append(dict(r, arm="g-px", images=ims, prompt=gpx_aux(r["prompt"])))
            continue
        k = seen.get(r["id"], 0)
        seen[r["id"]] = k + 1
        p = os.path.join(pdir, f"{r['id']}_o{k}.txt")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(gpx_text(open(r["prompt_path"], encoding="utf-8").read()))
        out.append(dict(r, arm="g-px", prompt_path=p, images=ims))
    dst = os.path.join(out_dir, name + ".jsonl")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    c = {"src": src, "rows": len(out), "control_rows": sum(r["kind"] == "control" for r in out),
         "aux_rows": sum(r["kind"] == "aux" for r in out), "images_drawn": len(drawn)}
    json.dump(c, open(dst + ".counts.json", "w"), indent=1)
    return c
