"""Per-episode validity checks of R2 output (pure, reads the files finalize() wrote).

valid_for_training = every structural check passes AND the oracle episode succeeded. Structural checks: frame
indices contiguous and on the 30 Hz grid (timing.tick_time), both cameras' JPEGs present for every frame at native
size, one R4 row per non-terminal frame and each passes stageb_data.check_row(hz=30), labels_v2 rows exactly at the
decision frames, npz arrays consistent and finite, verification targets at every decision frame k >= 10.
"""
from __future__ import annotations

import json
import os

import numpy as np

from ..train.stageb_data import check_row
from .timing import DEC_EVERY, HZ, is_decision, tick_time

NATIVE = {"cam_head": (672, 376), "cam_wrist_right": (424, 240)}
FIRST_FRAME_DIFF_MAX = 8.0  # grey levels; motion alone gave 1.7-3.7 on DEV, the dr seed-change transient 9-39


def _jpeg_size(path: str):
    """(width, height) from the JPEG SOF marker (no image library needed)."""
    with open(path, "rb") as f:
        data = f.read()
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        m = data[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return None


def validate_episode(folder: str, seed: int, cams=tuple(NATIVE), check_jpeg_size: bool = True) -> dict:
    base = f"{folder}/ep{seed}"
    err = []
    meta = json.load(open(base + ".meta.json", encoding="utf-8"))
    lines = [json.loads(x) for x in open(base + ".jsonl", encoding="utf-8")]
    rows = [json.loads(x) for x in open(f"{folder}/rows/ep{seed}.stageb.jsonl", encoding="utf-8")]
    labs = [json.loads(x) for x in open(f"{folder}/rows/ep{seed}.labels_v2.jsonl", encoding="utf-8")]
    K = len(lines) - 1
    ks = [ln["k"] for ln in lines]
    if ks != list(range(K + 1)):
        err.append("frame indices not contiguous from 0")
    tdev = max((abs(ln["t"] - tick_time(ln["k"])) for ln in lines), default=0.0)
    if tdev > 1e-6:
        err.append(f"frame time off the 30 Hz grid by {tdev:.2e} s")
    n_img = 0
    for ln in lines:
        for c in cams:
            rel = ln["images"].get(c)
            p = os.path.join(folder, rel) if rel else None
            if not p or not os.path.exists(p):
                err.append(f"k{ln['k']}: missing {c}")
                continue
            n_img += 1
            if check_jpeg_size and ln["k"] in (0, K) and _jpeg_size(p) != NATIVE.get(c, _jpeg_size(p)):
                err.append(f"k{ln['k']} {c}: size {_jpeg_size(p)} != native {NATIVE.get(c)}")
    if n_img != len(lines) * len(cams):
        err.append(f"images {n_img} != frames {len(lines)} x cams {len(cams)}")
    if [r["k"] for r in rows] != list(range(K)):
        err.append("stageb rows are not one per non-terminal frame")
    bad = 0
    for r in rows:
        try:
            check_row(r, hz=HZ)
        except ValueError as e:
            bad += 1
            if bad <= 3:
                err.append(f"row k{r['k']}: {e}")
    dec = [k for k in range(K + 1) if is_decision(k)]
    if [x["k"] for x in labs] != dec:
        err.append("labels_v2 rows != decision frames")
    miss_v = [ln["k"] for ln in lines if ln["k"] >= DEC_EVERY and ln["decision"] and "prev_step" not in ln["verify"]]
    if miss_v:
        err.append(f"verification target missing at {miss_v[:5]}")
    z = np.load(base + ".npz")
    for key in ("t", "q", "qd", "tau", "grip", "action"):
        a = z[key]
        if len(a) != K + 1 or not np.isfinite(a).all():
            err.append(f"npz {key}: length {len(a)} (want {K + 1}) or non-finite")
    if int(z["hold_n"][:K].sum()) != int(round((lines[-1]["t"] - lines[0]["t"]) / 0.01)):
        err.append("hold_n does not add up to the episode duration")
    warn = []
    try:  # renderer transient on the first frame (dr seed change): k0 -> k1 head image change far above motion
        from PIL import Image
        a, b = (np.asarray(Image.open(os.path.join(folder, lines[k]["images"]["cam_head"])).convert("L"), float)
                for k in (0, 1))
        d01 = float(np.abs(a - b).mean())
        if d01 > FIRST_FRAME_DIFF_MAX:
            warn.append(f"first-frame render transient: k0->k1 mean |diff| {d01:.1f} > {FIRST_FRAME_DIFF_MAX}")
    except Exception:  # noqa: BLE001  (no PIL / single frame: skip the soft check)
        d01 = None
    ok = not err
    return {"seed": seed, "folder": folder, "frames": K + 1, "rows": len(rows), "images": n_img,
            "k0_k1_head_diff": None if d01 is None else round(d01, 2), "warnings": warn,
            "decisions": len(labs), "row_errors": bad, "structural_ok": ok, "success": bool(meta.get("success")),
            "valid_for_training": bool(ok and meta.get("success")), "errors": err}


def stamp(folder: str, seed: int, report: dict) -> None:
    """Record the validation result in the meta file (merge() reads valid_for_training)."""
    p = f"{folder}/ep{seed}.meta.json"
    meta = json.load(open(p, encoding="utf-8"))
    meta["validation"] = {k: v for k, v in report.items() if k not in ("folder",)}
    meta["valid_for_training"] = report["valid_for_training"]
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    os.replace(tmp, p)
