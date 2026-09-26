"""Quality gates of the conversion (pure numpy): projected point on the gripper, 3D-centre error, segmentation sanity.
Gate values (docs/research/public_data_conversion_howto_2026-09-26.md 5): EE point on the gripper >= 95 % of frames
where it is in view; 3D centre error vs GT <= 2 cm (median) where GT exists."""
from __future__ import annotations

import numpy as np


def on_points(uv, ref, margin_px: float = 10.0) -> bool:
    """uv inside the bounding box of the finite reference points (e.g. MolmoBot's 10 gripper-geometry points),
    grown by margin_px."""
    ref = np.asarray(ref, float)
    ref = ref[np.isfinite(ref).all(1)]
    if not len(ref) or not np.isfinite(uv).all():
        return False
    lo, hi = ref.min(0) - margin_px, ref.max(0) + margin_px
    return bool(np.all(np.asarray(uv) >= lo) and np.all(np.asarray(uv) <= hi))


def near_points(uv, ref, k: float = 0.5, min_px: float = 8.0) -> bool:
    """uv within k x (bounding-box diagonal) of the nearest finite reference point: tolerates a TCP at the finger tips
    when the reference points sample only the gripper body (MolmoBot, eye check 2026-09-26)."""
    ref = np.asarray(ref, float)
    ref = ref[np.isfinite(ref).all(1)]
    if not len(ref) or not np.isfinite(uv).all():
        return False
    diag = float(np.linalg.norm(ref.max(0) - ref.min(0)))
    return bool(np.min(np.linalg.norm(ref - np.asarray(uv, float), axis=1)) <= max(k * diag, min_px))


def on_mask(uv, mask, r_px: int = 0) -> bool:
    """uv within r_px pixels of a True pixel of mask (e.g. the robot's gripper links in an instance segmentation)."""
    if not np.isfinite(uv).all():
        return False
    u, v = int(round(uv[0])), int(round(uv[1]))
    H, W = mask.shape
    u0, u1, v0, v1 = max(u - r_px, 0), min(u + r_px + 1, W), max(v - r_px, 0), min(v + r_px + 1, H)
    if u0 >= u1 or v0 >= v1:
        return False
    return bool(mask[v0:v1, u0:u1].any())


def rate(flags) -> dict:
    flags = list(flags)
    return {"n": len(flags), "pass": int(sum(bool(f) for f in flags)),
            "rate": round(sum(bool(f) for f in flags) / len(flags), 4) if flags else None}


def seg_sane(n_px: int, valid_frac: float, spread_m: float, min_px: int = 150, min_valid: float = 0.8,
             max_spread_m: float = 0.5) -> list:
    """Reasons a mask ∩ depth object sample is rejected (empty list = keep)."""
    out = []
    if n_px < min_px:
        out.append("small_mask")
    if valid_frac < min_valid:
        out.append("depth_holes")
    if spread_m > max_spread_m:
        out.append("mask_spread")
    return out


def err_stats(errs) -> dict:
    e = np.asarray([x for x in errs if x is not None and np.isfinite(x)], float)
    if not len(e):
        return {"n": 0}
    return {"n": int(len(e)), "median": round(float(np.median(e)), 4), "p90": round(float(np.percentile(e, 90)), 4),
            "le_0.02": round(float(np.mean(e <= 0.02)), 4)}
