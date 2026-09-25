"""S-E2E temporal context, OPT-IN (docs/stage3/prereg_se2e_temporal.md; research temporal_context_2026-09-25 §1 #1-#2).

Two factors on top of the S-E2E stage-B samples (se2e_data.load_se2e); with both off the samples are exactly the
baseline's (the loader delegates), and nothing here is read by the default training / runtime path:
  V  camera layout  LAYOUT_SINGLE = stageb_data.CAMERA_LAYOUT "D27v1" (baseline) |
                    LAYOUT_VIDEO2 "D27v2-video2": every camera = the 2-frame clip [t - DELTA_S, t] (nearest source
                    frame, 3 steps at 10 Hz; clamped at the episode start). Image entries become [label, now, prev];
                    se2e_temporal_model packs the pair into the ONE temporal patch (temporal_patch_size 2) that a
                    still image fills with two copies of itself, so the LLM visual token count is unchanged
                    (Qwen3-VL video processor output for [prev, now] = this packing, bit for bit: prereg §2).
  M  motion line    None (baseline) | MOTION_VER: one text line after the robot line,
                    "motion: arm=<still|slow|fast> gripper=<closing|still|opening>" from CAUSAL backward
                    differences (k - 1 -> k) of the recorded state (the rows' proprio.qd is a central difference
                    that reads frame k + 1 and is not used). Bins = train-split quantiles (fit_motion_bins), fixed
                    before training. Training replaces the line by MOTION_UNKNOWN with p = MOTION_DROPOUT
                    (motion_dropout, seeded per step); evaluation never drops it.
Rows: the S-E2E rows + hist_fields (tools/se2e_temporal.py augment -> /data/harvest/data/se2e_t/conv).
"""
from __future__ import annotations

import json
import os
import random

import numpy as np

from . import se2e_data as S
from . import stageb_data as D

LAYOUT_SINGLE = D.CAMERA_LAYOUT  # "D27v1"
LAYOUT_VIDEO2 = "D27v2-video2"
LAYOUTS = (LAYOUT_SINGLE, LAYOUT_VIDEO2)
DELTA_S = 0.3
MOTION_VER = "se2e-motion@v1"
MOTION_DROPOUT = 0.3
MOTION_UNKNOWN = "motion: arm=unknown gripper=unknown"
ARM_Q = (1.0 / 3.0, 2.0 / 3.0)  # arm speed tertiles -> still / slow / fast
GRIP_Q = 0.85  # |gripper openness rate| quantile -> still below, closing / opening above (60 % of train rows are
#                exactly 0 and q0.80 = 0.04 /s is jitter; q0.85 = 0.18 /s, q0.90 = 0.78 /s -- prereg §3, set from the input
#                distribution before any training)
SE2E_T_ROOT = "/data/harvest/data/se2e_t/conv"
VIDEO_LABEL = {c: D.CAM_LABEL[c][:-1] + f" (2 frames: t-{DELTA_S:g} s, t):" for c in D.CAM_LABEL}


# ------------------------------------------------------------------------------------------ rows
def prev_index(k: int, fps: float, delta_s: float = DELTA_S) -> int:
    return max(0, int(k) - int(round(delta_s * fps)))


def backward_velocity(x, k: int, fps: float) -> np.ndarray:
    """(x[k] - x[k-1]) * fps; 0 at k = 0 (causal: never reads k + 1)."""
    x = np.asarray(x, float)
    return np.zeros_like(x[0]) if k <= 0 else (x[k] - x[k - 1]) * fps


def hist_fields(row: dict, state, fps: float, names, prev_ref) -> dict:
    """Extra fields of one S-E2E row: the past frame index / paths (same cameras as the row) and the causal
    motion source of the active arm (7 joint velocities rad/s, gripper joint rate in the dataset's units/s)."""
    st = np.asarray(state, float)
    k, kp = row["k"], prev_index(row["k"], fps)
    ix = S.arm_index(names, row["arm"])
    ref = prev_ref(kp)
    return {"k_prev": kp, "dt_prev_s": round((k - kp) / fps, 6),
            "images_prev": {c: ref[c] for c in (row.get("images") or {})},
            "motion_src": {"qd_bwd": [float(v) for v in backward_velocity(st[:, ix[:7]], k, fps)],
                           "grip_rate_bwd": float(backward_velocity(st[:, ix[7]], k, fps))}}


# ------------------------------------------------------------------------------------------ motion line
def motion_values(row: dict):
    """(arm joint-speed norm rad/s, gripper openness rate 1/s; + = opening) of a row with motion_src."""
    m = row["motion_src"]
    src = D.grip_source(row) if "kind" in row else "sim_width_m"
    return float(np.linalg.norm(m["qd_bwd"])), float(D.grip_rate01(m["grip_rate_bwd"], src))


def fit_motion_bins(rows) -> dict:
    """Bins from the TRAIN split only: arm-speed tertiles, gripper |rate| GRIP_Q quantile."""
    vals = [motion_values(r) for r in rows if r.get("split") == "train"]
    arm = np.array([v[0] for v in vals])
    gr = np.abs([v[1] for v in vals])
    return {"version": MOTION_VER, "n": len(vals), "arm_speed": [float(np.quantile(arm, q)) for q in ARM_Q],
            "grip_rate": float(np.quantile(gr, GRIP_Q)), "arm_q": list(ARM_Q), "grip_q": GRIP_Q}


def motion_line(row: dict, bins: dict) -> str:
    a, g = motion_values(row)
    lo, hi = bins["arm_speed"]
    arm = "still" if a < lo else "slow" if a < hi else "fast"
    t = bins["grip_rate"]
    grip = "opening" if g > t else "closing" if g < -t else "still"
    return f"motion: arm={arm} gripper={grip}"


def motion_dropout(batch, step: int, seed: int, p: float = MOTION_DROPOUT) -> list:
    """Training batch with each sample's motion line replaced by MOTION_UNKNOWN with probability p (own RNG seeded
    by (seed, step): the data order RNG is not touched). Samples are not modified (shallow copies)."""
    if p <= 0:
        return list(batch)
    rng = random.Random(seed * 1_000_003 + step)
    out = []
    for s in batch:
        if "motion_alt" in s and rng.random() < p:
            alt = s["motion_alt"]
            out.append({**s, "context": {**s["context"], "text": alt["context_text"]},
                        "items": [{**it, "text": t} for it, t in zip(s["items"], alt["item_texts"])]})
        else:
            out.append(s)
    return out


# ------------------------------------------------------------------------------------------ loader
def _video_images(row: dict, ims: list, image_root: str, prev_root: str) -> list:
    out = []
    by_path = {os.path.join(image_root, p) if image_root else p: c for c, p in row["images"].items()}
    for lab, now in ims:
        c = by_path[now]
        prev = row["images_prev"][c]
        out.append([VIDEO_LABEL[c], now, os.path.join(prev_root, prev) if prev_root else prev])
    return out


def load_se2e_t(rows_path: str, image_root: str = "", prev_root: str = "", layout: str = LAYOUT_SINGLE,
                bins: dict | None = None, labels: bool = True, wrist: bool = True, hz: int | None = None) -> list:
    """se2e_data.load_se2e samples of augmented rows, with the V / M options. Both off -> load_se2e itself."""
    if layout not in LAYOUTS:
        raise ValueError(f"layout {layout!r}: one of {LAYOUTS}")
    base = S.load_se2e(rows_path, image_root=image_root, labels=labels, wrist=wrist, hz=hz)
    if layout == LAYOUT_SINGLE and bins is None:
        return base
    rows = {}
    for x in open(rows_path, encoding="utf-8"):
        r = json.loads(x)
        rows[f"{r['kind']}_ep{r['seed']}_k{r['k']}"] = r
    for s in base:
        r = rows[s["key"]]
        if layout == LAYOUT_VIDEO2:
            ims = _video_images(r, s["context"]["images"], image_root, prev_root)
            s["context"]["images"] = ims
            for it in s["items"]:
                it["images"] = ims
        if bins is not None:
            ctx0 = s["context"]["text"]
            line = motion_line(r, bins)
            ctx, unk = ctx0 + "\n" + line, ctx0 + "\n" + MOTION_UNKNOWN
            alt = []
            for it in s["items"]:
                if not it["text"].startswith(ctx0):
                    raise ValueError(f"{s['key']}: question text does not start with the context")
                tail = it["text"][len(ctx0):]
                it["text"] = ctx + tail
                alt.append(unk + tail)
            s["context"]["text"] = ctx
            s["motion_alt"] = {"context_text": unk, "item_texts": alt}
    return base


def load_for_training_t(se2e_t_root: str = SE2E_T_ROOT, image_root: str = D.SE2E_ROOT, kinds: str = "RB1,RB2",
                        layout: str = LAYOUT_SINGLE, bins: dict | None = None, labels: bool = True,
                        wrist: bool = True):
    """(samples, hz): rows from se2e_t_root (baseline rows + hist_fields), current frames under image_root (the
    S-E2E conversion, not copied), past frames under se2e_t_root."""
    hz = D.DATA_HZ["se2e"]
    out = []
    for kind in [k for k in kinds.split(",") if k]:
        out += load_se2e_t(S.rows_path(se2e_t_root, kind), image_root=image_root, prev_root=se2e_t_root,
                           layout=layout, bins=bins, labels=labels, wrist=wrist, hz=hz)
    return out, hz


# ------------------------------------------------------------------------------------------ transition stratum
def transition_flags(labels, k: int, steps: int = 3):
    """prereg: snapshot k is a TRANSITION when some question's label (same rule, frame-level) differs between k and
    k + j for some j in 1..steps (0.1-0.3 s; the next decision 0.33 s -> 3 steps at 10 Hz). Returns (any, per q)."""
    per = {}
    for q in S.QUESTIONS:
        per[q] = any(labels[k + j][q] != labels[k][q] for j in range(1, steps + 1) if k + j < len(labels))
    return any(per.values()), per
