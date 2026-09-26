"""T0 pixel-only: MolmoAct released rows (allenai/MolmoAct-Pretraining-Mixture, CC BY 4.0; OXE BC-Z / RT-1 / Bridge +
auxiliary_trace) -> our 2-D gripper-trace QA (frame: pixel, camera: unknown).

Row formats (measured 2026-09-27): columns image{bytes}, conversations{from, value}, annotation.
  - 'what is the trajectory ...' answers carry '[[x, y], ...]' (1-5 points, 0-255 of the image size);
  - trajectory-conditioned rows carry the trace in `annotation`;
  - action-reasoning rows carry depth tokens + trace + action tokens in the answer (the trace is the first [[...]]).
Pixels = value * (size - 1) / 255 (the MolmoAct loader's olmo/data/image_preprocessor.load_image convention).
Quality filter (MolmoAct has none): 2..5 points, consecutive jumps <= 40 % of the image diagonal, total path
<= 1.5 x diagonal, no sharp (> 135 deg) reversal between two moves > 5 % of the diagonal. The Molmo pointing labels behind these traces are unverified per row (howto 1.2).
"""
from __future__ import annotations

import json
import re

import numpy as np

_TR = re.compile(r"\[\s*(\[\s*\d+\s*,\s*\d+\s*\](?:\s*,\s*\[\s*\d+\s*,\s*\d+\s*\])*)\s*\]")
JUMP_FRAC, PATH_FRAC = 0.40, 1.5
REV_FRAC, REV_DEG = 0.05, 135.0  # consecutive moves > 5 % of the diagonal turning back by > 135 deg = pointing noise


def parse_trace(text):
    if not text:
        return None
    m = _TR.search(text)
    if not m:
        return None
    return [[int(a), int(b)] for a, b in re.findall(r"\[\s*(\d+)\s*,\s*(\d+)\s*\]", m.group(0))]


def to_px(tr, W, H):
    return [[x * (W - 1) / 255.0, y * (H - 1) / 255.0] for x, y in tr]


def trace_ok(px, W, H) -> bool:
    p = np.asarray(px, float)
    if not (2 <= len(p) <= 5):
        return False
    diag = float(np.hypot(W, H))
    d = np.diff(p, axis=0)
    steps = np.linalg.norm(d, axis=1)
    if not (steps.max() <= JUMP_FRAC * diag and steps.sum() <= PATH_FRAC * diag):
        return False
    for a, b, la, lb in zip(d[:-1], d[1:], steps[:-1], steps[1:]):  # zig-zag: a sharp reversal between two real moves
        if la > REV_FRAC * diag and lb > REV_FRAC * diag and a @ b / (la * lb) < np.cos(np.radians(REV_DEG)):
            return False
    return True


def task_of(q: str) -> str:
    m = re.search(r"The task is (.+?)\.", q or "")
    return m.group(1).strip() if m else ""


def record(source, task, px, W, H, image, rid):
    q = (f"source: {source}\nframe: pixel\nCAMERAS\n- Image 1: camera, {W}x{H} px; camera: unknown (no calibration).\n"
         f"TASK: {task}\nWhere will the robot gripper go? Give its path in image 1 as up to 5 points, from where it is "
         f"now onward.\nReturn JSON only.")
    return {"id": rid, "kind": "qa_xemb", "qa_kind": "ee_trace_detected", "source": source, "frame": "pixel",
            "prompt": q, "images": [image], "answer": json.dumps({"trace": [[int(round(u)), int(round(v))]
                                                                            for u, v in px]})}


def convert(files: dict, out: str, per_source: int = 2000, seed: int = 0, stride: int = 10) -> dict:
    """files = {source_name: parquet path}; samples up to per_source filtered traces from each."""
    import io
    import os

    import pyarrow.parquet as pq
    from PIL import Image
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    rng = np.random.default_rng(seed)
    recs, stats, items = [], {}, []
    for src, path in files.items():
        pf = pq.ParquetFile(path)
        groups = rng.permutation(pf.num_row_groups)
        n_seen = n_trace = n_keep = 0
        for gi in groups:
            if n_keep >= per_source:
                break
            for ri, r in enumerate(pf.read_row_group(int(gi)).to_pylist()):
                if ri % stride:  # neighbouring rows are consecutive frames of one episode
                    continue
                if n_keep >= per_source:
                    break
                n_seen += 1
                vals = (r.get("conversations") or {}).get("value") or []
                tr = parse_trace(r.get("annotation")) or (parse_trace(vals[1]) if len(vals) > 1 else None)
                if tr is None:
                    continue
                n_trace += 1
                im = Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB")
                W, H = im.size
                px = to_px(tr, W, H)
                if not trace_ok(px, W, H):
                    continue
                n_keep += 1
                img = os.path.join(out, "frames", f"mact_{src}_{gi}_{ri}.jpg")
                im.save(img, quality=90)
                recs.append(record(f"molmoact/{src}", task_of(vals[0] if vals else ""), px, W, H, img,
                                   f"mact_{src}_{gi}_{ri}"))
                if len(items) < 36:
                    items.append({"img": img, "trace": px, "label": f"{src} {task_of(vals[0] if vals else '')[:30]}"})
        stats[src] = {"rows_seen": n_seen, "with_trace": n_trace, "kept": n_keep,
                      "keep_rate_of_traces": round(n_keep / max(1, n_trace), 3)}
    with open(os.path.join(out, "records_P.jsonl"), "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    return {"n_P": len(recs), "per_source": stats}, items
