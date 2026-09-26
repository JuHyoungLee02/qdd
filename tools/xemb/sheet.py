"""Overlay contact sheets for eye checks (cv2). Marks: red ring = projected EE/TCP, blue dots = reference gripper
points (dataset GT) or gripper mask outline, orange line = approach axis (8 cm), green = object point, cyan cross =
projected GT object centre, yellow = place point, magenta X = C' target (projected)."""
from __future__ import annotations

import os

import cv2
import numpy as np


def _p(v):
    return (int(round(v[0])), int(round(v[1])))


def draw(item) -> np.ndarray:
    im = cv2.imread(item["img"])
    if im is None:
        return None
    if item.get("mask") is not None:
        cs, _ = cv2.findContours(item["mask"].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(im, cs, -1, (255, 128, 0), 1)
    ref = item.get("ref")
    if ref is not None:
        for q in np.asarray(ref, float):
            if np.isfinite(q).all():
                cv2.circle(im, _p(q), 2, (255, 0, 0), -1)
    for key, col in (("obj", (0, 255, 0)), ("place", (0, 255, 255))):
        if item.get(key) is not None:
            cv2.circle(im, _p(item[key]), 6, col, 2)
    if item.get("obj_proj") is not None and np.isfinite(item["obj_proj"]).all():
        cv2.drawMarker(im, _p(item["obj_proj"]), (255, 255, 0), cv2.MARKER_CROSS, 14, 2)
    if item.get("ee") is not None:
        cv2.circle(im, _p(item["ee"]), 7, (0, 0, 255), 2)
        if item.get("ax") is not None and np.isfinite(item["ax"]).all():
            cv2.line(im, _p(item["ee"]), _p(item["ax"]), (0, 128, 255), 2)
    if item.get("tgt") is not None and np.isfinite(item["tgt"]).all():
        cv2.drawMarker(im, _p(item["tgt"]), (255, 0, 255), cv2.MARKER_TILTED_CROSS, 16, 2)
    if item.get("crop"):  # zoom on the EE / target so the eye check can see the marks (MolmoBot: gripper ~30 px)
        f = next((item[k] for k in ("ee", "tgt", "obj") if item.get(k) is not None
                  and np.isfinite(item[k]).all()), None)
        if f is not None:
            r = item["crop"] // 2
            H, W = im.shape[:2]
            cx, cy = int(min(max(f[0], r), W - r)), int(min(max(f[1], r), H - r))
            im = np.ascontiguousarray(im[max(cy - r, 0):cy + r, max(cx - r, 0):cx + r])
    cv2.putText(im, item.get("label", ""), (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
    cv2.putText(im, item.get("label", ""), (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return im


def sheets(items, out_prefix: str, per: int = 12, cols: int = 3, tile_w: int = 480) -> list:
    paths = []
    for s in range(0, len(items), per):
        tiles = []
        for it in items[s:s + per]:
            im = draw(it)
            if im is None:
                continue
            h = int(im.shape[0] * tile_w / im.shape[1])
            tiles.append(cv2.resize(im, (tile_w, h)))
        if not tiles:
            continue
        th = max(t.shape[0] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, th - t.shape[0], 0, 0, cv2.BORDER_CONSTANT) for t in tiles]
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[r:r + cols]) for r in range(0, len(tiles), cols)]
        p = f"{out_prefix}_{s // per:02d}.jpg"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        cv2.imwrite(p, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
        paths.append(p)
    return paths
