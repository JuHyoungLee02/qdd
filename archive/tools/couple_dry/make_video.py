"""Dry-run videos and frame sheets (book rule: verify with frames). Needs cv2 (pod: /data/harvest/venv_vllm/bin/python).

  frames: python tools/couple_dry/make_video.py frames --dir <out>/video/<variant>/<policy>/<scene> --mp4 X.mp4 \
              --sheet X.jpg [--fps 6] [--n 12]
          head | right wrist side by side per sampled time (dry_closed.py writes <t>_<phase>_<cam>.jpg)
  requests: python tools/couple_dry/make_video.py requests --sidecar <trial>.jsonl --sheet X.jpg [--n 6]
          the images the stream model actually received (overlay drawn), from the content-addressed blobs
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import cv2
import numpy as np

CAMS = ("cam_head", "cam_wrist_right")
H = 240


def _fit(img, h=H):
    return cv2.resize(img, (int(img.shape[1] * h / img.shape[0]), h))


def _label(img, text, y=18):
    cv2.putText(img, text, (6, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (6, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def frame_rows(d):
    by = defaultdict(dict)
    for p in sorted(glob.glob(os.path.join(d, "*.jpg"))):
        stem = os.path.basename(p)[:-4]
        for cam in CAMS:
            if stem.endswith("_" + cam):
                t, ph = stem[:-len(cam) - 1].split("_", 1)
                by[(float(t), ph)][cam] = p
    rows = []
    for (t, ph), m in sorted(by.items()):
        imgs = [_fit(cv2.imread(m[c])) for c in CAMS if c in m]
        if imgs:
            rows.append(_label(np.hstack(imgs), f"t={t:.1f}s {ph}"))
    return rows


def sheet(rows, n, path, cols=2):
    if not rows:
        return 0
    idx = np.linspace(0, len(rows) - 1, min(n, len(rows))).round().astype(int)
    pick = [rows[i] for i in idx]
    w = max(r.shape[1] for r in pick)
    pick = [np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0))) for r in pick]
    while len(pick) % cols:
        pick.append(np.zeros_like(pick[0]))
    grid = np.vstack([np.hstack(pick[i:i + cols]) for i in range(0, len(pick), cols)])
    cv2.imwrite(path, grid, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return len(idx)


def cmd_frames(a):
    rows = frame_rows(a.dir)
    if a.mp4 and rows:
        w = max(r.shape[1] for r in rows)
        vw = cv2.VideoWriter(a.mp4, cv2.VideoWriter_fourcc(*"mp4v"), a.fps, (w, H))
        for r in rows:
            vw.write(np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0))))
        vw.release()
    n = sheet(rows, a.n, a.sheet) if a.sheet else 0
    print(json.dumps({"frames": len(rows), "sheet_n": n, "mp4": a.mp4}))


def cmd_requests(a):
    blobs = os.path.join(os.path.dirname(a.sidecar), "blobs")
    rows = []
    for x in open(a.sidecar, encoding="utf-8"):
        r = json.loads(x)
        if r.get("type") != "couple" or r.get("couple_kind") != "answer":
            continue
        ims = r.get("image_sha256") or {}
        tiles = []
        for cam in ("cam_head", "cam_wrist_left", "cam_wrist_right"):
            p = os.path.join(blobs, f"{ims.get(cam)}.jpg")
            if cam in ims and os.path.exists(p):
                tiles.append(_label(_fit(cv2.imread(p)), cam))
        if tiles:
            cmd = r.get("command") or ("schema_error" if r.get("schema_error") else r.get("error") or "?")
            tiles[0] = _label(tiles[0], f"#{r['no']} t={r['t_state']:.1f}s -> {cmd} gate={r.get('gate')}", y=40)
            rows.append(np.hstack(tiles))
    n = sheet(rows, a.n, a.sheet, cols=1)
    print(json.dumps({"answers_with_images": len(rows), "sheet_n": n}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("frames")
    f.add_argument("--dir", required=True)
    f.add_argument("--mp4", default="")
    f.add_argument("--sheet", default="")
    f.add_argument("--fps", type=float, default=6.0)
    f.add_argument("--n", type=int, default=12)
    r = sub.add_parser("requests")
    r.add_argument("--sidecar", required=True)
    r.add_argument("--sheet", required=True)
    r.add_argument("--n", type=int, default=6)
    a = ap.parse_args(argv)
    (cmd_frames if a.cmd == "frames" else cmd_requests)(a)


if __name__ == "__main__":
    main()
