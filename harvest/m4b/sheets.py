"""Frame sheets for FI-DEV checks (pod): per episode, head + wrist frames around the injection / onset with the
phase and the truth predicates written on each frame.

  python -m harvest.m4b.sheets --root DIR --seed 0 --conds all --out DIR [--n 8]
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from . import spec as FS

SHORT = {"on_tp": "on", "contact_tp": "ct", "lifted_t": "lift", "near_tp": "near", "above_tp": "abv",
         "gripper_open": "gopen", "holding_t": "hold", "lifted_holding": "lh", "contact_stall": "stall"}


def pick(snaps, fi, n):
    t0 = fi.get("t_inject")
    if t0 is None:
        idx = np.linspace(0, len(snaps) - 1, n).round().astype(int)
        return sorted(set(idx.tolist()))

    def at(t):
        return next((i for i, s in enumerate(snaps) if s["t"] >= t - 1e-9), len(snaps) - 1)
    i0 = at(t0)
    want = [i0 - 1, i0, i0 + 2]
    i1 = at(fi["onset"]) if fi.get("onset") is not None else i0 + 3
    want += [i1 - 1, i1, i1 + 1, i1 + 3, len(snaps) - 1]
    return sorted({min(max(i, 0), len(snaps) - 1) for i in want})[:n]


def sheet(root, cond, seed, out, n=8, w=256):
    from PIL import Image, ImageDraw
    d = f"{root}/{cond}"
    fi = json.load(open(f"{d}/ep{seed}.fi.json"))
    lines = [json.loads(x) for x in open(f"{d}/ep{seed}.jsonl")]
    snaps = fi["snaps"]
    idx = pick(snaps, fi, n)
    rows = []
    for i in idx:
        ims = []
        for cam in ("cam_head", "cam_wrist_right"):
            im = Image.open(os.path.join(d, lines[i]["images"][cam])).convert("RGB")
            h = int(round(w * im.height / im.width))
            ims.append(im.resize((w, h)))
        rows.append((snaps[i], ims))
    H = sum(max(im.height for im in ims) for _, ims in rows)
    sh = Image.new("RGB", (2 * w, H + 18), (0, 0, 0))
    y = 18
    ImageDraw.Draw(sh).text((4, 3), f"{cond} seed{seed} {fi['kind']} inject={fi['t_inject']} onset={fi['onset']} "
                                    f"success={fi['success']}", fill=(255, 255, 0))
    for s, ims in rows:
        tr = s["truth"]
        txt = f"t={s['t']:.2f} {s['phase']} " + " ".join(f"{SHORT[p]}={'?' if tr[p] is None else int(tr[p])}"
                                                            for p in FS.PREDS)
        viol = FS.violations(s["phase"], tr)
        for j, im in enumerate(ims):
            sh.paste(im, (j * w, y))
        dr = ImageDraw.Draw(sh)
        dr.text((4, y + 2), txt[:60], fill=(255, 255, 255))
        dr.text((4, y + 14), txt[60:], fill=(255, 255, 255))
        if viol:
            dr.text((4, y + 26), "VIOL " + ",".join(viol), fill=(255, 60, 60))
        y += max(im.height for im in ims)
    os.makedirs(out, exist_ok=True)
    p = f"{out}/{cond}_s{seed}.jpg"
    sh.save(p, quality=80)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--conds", default="all")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=8)
    a = ap.parse_args(argv)
    conds = FS.CONDITIONS if a.conds == "all" else a.conds.split(",")
    for c in conds:
        if os.path.exists(f"{a.root}/{c}/ep{a.seed}.fi.json"):
            print(sheet(a.root, c, a.seed, a.out, a.n))


if __name__ == "__main__":
    main()
