"""Exposure check of gate frames (prereg_l8d change 14): per episode the first head frame (img1_head_ring.png of c000)
is over-exposed when > OVER_FRAC of its pixels are saturated (max channel >= 250) and too dark when its mean luma
< DARK_LUMA. Gate: both shares <= MAX_SHARE. usage: python exposure.py <gate root> [<out.json>]"""
import glob
import json
import os
import sys

import numpy as np

OVER_FRAC, DARK_LUMA, MAX_SHARE = 0.25, 45.0, 0.10


def frame_stats(rgb: np.ndarray) -> dict:
    rgb = np.asarray(rgb, float)
    sat = float((rgb.max(axis=2) >= 250).mean())
    luma = float((0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).mean())
    return {"sat_frac": round(sat, 4), "luma": round(luma, 1), "over": sat > OVER_FRAC, "dark": luma < DARK_LUMA}


def main(root: str, out: str | None = None) -> dict:
    from PIL import Image
    rows = {}
    for p in sorted(glob.glob(os.path.join(root, "**", "calls", "c000", "img1_head_ring.png"), recursive=True)):
        ep = os.path.dirname(os.path.dirname(os.path.dirname(p)))
        rows[os.path.relpath(ep, root)] = frame_stats(np.asarray(Image.open(p).convert("RGB")))
    n = max(len(rows), 1)
    res = {"n": len(rows), "over_share": round(sum(r["over"] for r in rows.values()) / n, 3),
           "dark_share": round(sum(r["dark"] for r in rows.values()) / n, 3), "episodes": rows}
    res["pass"] = res["n"] > 0 and res["over_share"] <= MAX_SHARE and res["dark_share"] <= MAX_SHARE
    if out:
        json.dump(res, open(out, "w"), indent=1)
    return res


if __name__ == "__main__":
    r = main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps({k: r[k] for k in ("n", "over_share", "dark_share", "pass")}))
