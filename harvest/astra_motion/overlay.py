"""Model-input image annotations (robot FK + camera calibration only, never object ground truth):
- pixel rulers on the top and left borders (ticks every 50 px, labels every 100 px);
- the current-TCP marker (cyan ring + cross, black outline; no scene object is cyan);
- coupling spec §13 motion overlay, thin and semi-transparent: the last ~3 s TCP trace (fading cyan line), the
  executor's current motion direction (yellow arrow, 5 cm) and the last Astra offset direction (orange arrow);
- on the RIGHT wrist view (the camera looks between the fingers, so anything drawn at the TCP would cover the object
  being grasped) nothing is drawn at the TCP: the two directions are drawn as arrows in a corner inset instead.
"""
from __future__ import annotations

from io import BytesIO

import numpy as np

from .geometry import Cam, project

CYAN = (0, 255, 255)
YELLOW = (255, 230, 0)
ORANGE = (255, 120, 0)
INSET = 56  # px, corner inset size on the right wrist view
ALPHA = 150


def _px(cam, p):
    u, v, z = project(cam, p)
    return (u, v) if z > 0 and np.isfinite(u) else None


def _arrow(d, a, b, col, width=2):
    d.line([a, b], fill=col + (ALPHA,), width=width)
    v = np.asarray(b, float) - np.asarray(a, float)
    n = float(np.linalg.norm(v))
    if n < 1e-6:
        return
    v /= n
    L = min(7.0, 0.4 * n)
    for s in (+1, -1):
        w = np.array([v[0] * np.cos(0.5) - s * v[1] * np.sin(0.5), s * v[0] * np.sin(0.5) + v[1] * np.cos(0.5)])
        d.line([tuple(b), tuple(np.asarray(b) - L * w)], fill=col + (ALPHA,), width=width)


def annotate(img: np.ndarray, cam: Cam | None, tcp=None, rulers: bool = True, marks=None, trace=None,
             exec_dir=None, astra_dir=None, wrist_inset: bool = False, show_tcp: bool = True) -> np.ndarray:
    """Copy of img with the annotations. trace = TCP positions (oldest first); exec_dir / astra_dir = base-frame
    motion vectors (drawn as 5 cm arrows from the TCP, or in the corner inset when wrist_inset); marks = [(3D point,
    text)] (videos only)."""
    from PIL import Image, ImageDraw
    base = Image.fromarray(np.ascontiguousarray(img).copy()).convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    W, H = base.size
    if cam is not None and trace is not None and len(trace) >= 2 and not wrist_inset:
        pts = [_px(cam, p) for p in trace]
        for k in range(1, len(pts)):
            if pts[k - 1] is None or pts[k] is None:
                continue
            a = int(40 + (ALPHA - 40) * k / (len(pts) - 1))  # older = fainter
            d.line([pts[k - 1], pts[k]], fill=CYAN + (a,), width=1)
    dirs = [(exec_dir, YELLOW), (astra_dir, ORANGE)]
    if cam is not None and tcp is not None:
        if wrist_inset:
            d.rectangle([W - INSET, 0, W - 1, INSET - 1], fill=(0, 0, 0, 110))
            c = np.array([W - INSET / 2, INSET / 2])
            for vec, col in dirs:
                if vec is None or np.linalg.norm(vec) < 1e-9:
                    continue
                v2 = cam.R.T @ np.asarray(vec, float)  # image-plane direction (x right, y down)
                if np.linalg.norm(v2[:2]) < 1e-9:
                    d.ellipse([c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4], outline=col + (ALPHA,), width=2)
                    continue
                e = v2[:2] / np.linalg.norm(v2[:2]) * (INSET / 2 - 6)
                _arrow(d, tuple(c), tuple(c + e), col)
        else:
            p0 = _px(cam, tcp)
            for vec, col in dirs:
                if vec is None or np.linalg.norm(vec) < 1e-9 or p0 is None:
                    continue
                p1 = _px(cam, np.asarray(tcp, float) + np.asarray(vec, float) / np.linalg.norm(vec) * 0.05)
                if p1 is not None:
                    _arrow(d, p0, p1, col)
    out = Image.alpha_composite(base, layer).convert("RGB")
    d = ImageDraw.Draw(out)
    if rulers:
        for u in range(0, W, 50):
            L = 7 if u % 100 == 0 else 4
            d.line([(u, 0), (u, L)], fill=(0, 0, 0), width=3)
            d.line([(u, 0), (u, L)], fill=(255, 255, 255), width=1)
            if u % 100 == 0 and u > 0:
                d.text((u + 2, 1), str(u), fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        for v in range(0, H, 50):
            L = 7 if v % 100 == 0 else 4
            d.line([(0, v), (L, v)], fill=(0, 0, 0), width=3)
            d.line([(0, v), (L, v)], fill=(255, 255, 255), width=1)
            if v % 100 == 0 and v > 0:
                d.text((9, v - 5), str(v), fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    for p, text in (marks or []):
        if cam is None:
            continue
        u, v, z = project(cam, p)
        if z > 0 and np.isfinite(u) and -20 < u < W + 20 and -20 < v < H + 20:
            d.ellipse([u - 4, v - 4, u + 4, v + 4], outline=(255, 120, 0), width=2)
            d.text((u + 5, v + 2), text, fill=(255, 160, 60), stroke_width=1, stroke_fill=(0, 0, 0))
    if tcp is not None and cam is not None and show_tcp and not wrist_inset:
        u, v, z = project(cam, tcp)
        if z > 0 and np.isfinite(u) and 0 <= u < W and 0 <= v < H:
            r = 7
            d.ellipse([u - r, v - r, u + r, v + r], outline=(0, 0, 0), width=3)
            d.ellipse([u - r, v - r, u + r, v + r], outline=CYAN, width=1)
            d.line([(u - r - 4, v), (u + r + 4, v)], fill=CYAN, width=1)
            d.line([(u, v - r - 4), (u, v + r + 4)], fill=CYAN, width=1)
    return np.asarray(out)


def png_bytes(img: np.ndarray) -> bytes:
    from PIL import Image
    b = BytesIO()
    Image.fromarray(np.ascontiguousarray(img)).save(b, format="PNG")
    return b.getvalue()
