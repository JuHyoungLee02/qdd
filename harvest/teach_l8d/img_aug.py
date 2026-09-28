"""L8S camera / sensor realism at build time (prereg_l8d change 17, user-log 181): per image a seeded draw of exposure
gain, white balance, sensor noise, mild blur and JPEG compression. Geometry is untouched (points and depth stay
valid): only the pixel values change. aug_rows() rewrites a JSONL's image paths to augmented copies."""
from __future__ import annotations

import hashlib
import io
import json
import os

import numpy as np

GAIN = (0.80, 1.20)
WB = (0.93, 1.07)  # per-channel multiplier
NOISE_SD = (0.0, 4.0)  # 8-bit units
BLUR_P, BLUR_SIGMA = 0.3, (0.3, 0.8)
JPEG_Q = (60, 95)


def params(key: str) -> dict:
    r = np.random.default_rng(int(hashlib.sha256(f"l8s-img:{key}".encode()).hexdigest()[:12], 16))
    return {"gain": float(r.uniform(*GAIN)), "wb": [float(v) for v in r.uniform(*WB, 3)],
            "noise_sd": float(r.uniform(*NOISE_SD)),
            "blur": float(r.uniform(*BLUR_SIGMA)) if r.random() < BLUR_P else 0.0,
            "jpeg_q": int(r.integers(JPEG_Q[0], JPEG_Q[1] + 1)), "noise_seed": int(r.integers(2 ** 31))}


def augment(img, p: dict):
    """PIL RGB image -> augmented PIL image (JPEG round trip)."""
    from PIL import Image, ImageFilter
    a = np.asarray(img.convert("RGB"), float) * p["gain"] * np.asarray(p["wb"])[None, None, :]
    if p["noise_sd"] > 0:
        a = a + np.random.default_rng(p["noise_seed"]).normal(0.0, p["noise_sd"], a.shape)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if p["blur"] > 0:
        out = out.filter(ImageFilter.GaussianBlur(p["blur"]))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=p["jpeg_q"])
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def aug_rows(src: str, dst: str, img_dir: str) -> dict:
    """Every row's images -> augmented JPEG copies in img_dir (one draw per (row id, image index)); -> counts."""
    from PIL import Image
    os.makedirs(img_dir, exist_ok=True)
    n = 0
    with open(src) as fi, open(dst, "w", newline="\n") as fo:
        for line in fi:
            r = json.loads(line)
            ims = []
            for i, p in enumerate(r.get("images", [])):
                key = f"{r.get('id', n)}:{i}"
                q = os.path.join(img_dir, hashlib.sha256(key.encode()).hexdigest()[:20] + ".jpg")
                if not os.path.exists(q):
                    augment(Image.open(p), params(key)).save(q, "JPEG", quality=95)
                ims.append(q)
            r["images"], r["img_aug"] = ims, True
            fo.write(json.dumps(r) + "\n")
            n += 1
    return {"rows": n, "dst": dst}
