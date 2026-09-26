"""Head-view overlay of the Astra-solo arm, drawn by code from the camera calibration and the robot's own kinematics
only (never from object ground truth):
- a WHITE GRID lying ON THE TABLE SURFACE (z = table top) in robot-frame coordinates: lines every 5 cm over the
  workspace, labels every 10 cm ("x=0.40" / "y=-0.20", metres) -- lets Astra read an object's (x, y) at its base
  instead of guessing depth from perspective (prompt_health.md Q1: x-sign errors from a lifted TCP, F5);
- the current TCP (white ring with a black outline);
- the DROP LINE: a white dotted line from the TCP straight down to the table, ending in a small filled white dot at
  the table point directly below the TCP.
Colours: white / black only (the scene's objects and dr distractors are coloured; pitfalls P77, P83).
The right wrist view is sent without any drawing (it looks between the fingers).
"""
from __future__ import annotations

import numpy as np

from ..astra_motion.executor import SAFE_X, SAFE_Y
from ..astra_motion.geometry import project

WHITE, BLACK = (255, 255, 255), (0, 0, 0)
GRID_STEP = 0.05
LABEL_STEP = 0.10


def grid_values():
    xs = [round(x, 2) for x in np.arange(SAFE_X[0], SAFE_X[1] + 1e-9, GRID_STEP)]
    ys = [round(y, 2) for y in np.arange(SAFE_Y[0], SAFE_Y[1] + 1e-9, GRID_STEP)]
    return xs, ys


def _px(cam, p):
    u, v, z = project(cam, p)
    return (u, v) if z > 0 and np.isfinite(u) else None


def label(axis: str, v: float) -> str:
    """x=0.40 / y=-0.20 / y=+0.10 (explicit metres; y keeps its sign)."""
    return f"x={v:.2f}" if axis == "x" else f"y={v:+.2f}"


def _inside(cam, p) -> bool:
    return p is not None and 0 <= p[0] < cam.W and 0 <= p[1] < cam.H


def head_overlay(img: np.ndarray, cam, table_z: float, tcp=None):
    """-> (annotated copy, list of drawn element names in drawing order)."""
    from PIL import Image, ImageDraw
    base = Image.fromarray(np.ascontiguousarray(img).copy()).convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    xs, ys = grid_values()
    for x in xs:
        a, b = _px(cam, [x, ys[0], table_z]), _px(cam, [x, ys[-1], table_z])
        if a and b:
            d.line([a, b], fill=WHITE + ((150 if abs(round(x / LABEL_STEP) * LABEL_STEP - x) < 1e-9 else 80),), width=1)
    for y in ys:
        a, b = _px(cam, [xs[0], y, table_z]), _px(cam, [xs[-1], y, table_z])
        if a and b:
            d.line([a, b], fill=WHITE + ((150 if abs(round(y / LABEL_STEP) * LABEL_STEP - y) < 1e-9 else 80),), width=1)
    drawn = ["grid"]
    if tcp is not None:
        tcp = np.asarray(tcp, float)
        top, foot = _px(cam, tcp), _px(cam, [tcp[0], tcp[1], table_z])
        if top and foot:
            n = 14
            for k in range(0, n, 2):  # dotted
                p = np.asarray(top) + (np.asarray(foot) - np.asarray(top)) * k / n
                q = np.asarray(top) + (np.asarray(foot) - np.asarray(top)) * (k + 1) / n
                d.line([tuple(p), tuple(q)], fill=WHITE + (230,), width=2)
            d.ellipse([foot[0] - 3, foot[1] - 3, foot[0] + 3, foot[1] + 3], fill=WHITE + (255,), outline=BLACK + (255,))
        if _inside(cam, top):
            d.ellipse([top[0] - 8, top[1] - 8, top[0] + 8, top[1] + 8], outline=BLACK + (255,), width=4)
            d.ellipse([top[0] - 8, top[1] - 8, top[0] + 8, top[1] + 8], outline=WHITE + (255,), width=2)
            drawn.append("tcp")
        if _inside(cam, top) and _inside(cam, foot):  # the legend's drop dot is visible
            drawn.append("drop")
    out = Image.alpha_composite(base, layer)
    dt = ImageDraw.Draw(out)
    for x in xs:  # labels on top, along the far (+y) and near edges
        if abs(round(x / LABEL_STEP) * LABEL_STEP - x) < 1e-9:
            p = _px(cam, [x, ys[-1], table_z])
            if p:
                dt.text((p[0] + 2, p[1] - 12), label("x", x), fill=WHITE, stroke_width=2, stroke_fill=BLACK)
    for y in ys:
        if abs(round(y / LABEL_STEP) * LABEL_STEP - y) < 1e-9:
            p = _px(cam, [xs[-1], y, table_z])
            if p:
                dt.text((p[0] + 2, p[1] - 12), label("y", y), fill=WHITE, stroke_width=2, stroke_fill=BLACK)
    return np.asarray(out.convert("RGB")), drawn


def png_bytes(img: np.ndarray) -> bytes:
    from ..astra_motion.overlay import png_bytes as pb
    return pb(img)
