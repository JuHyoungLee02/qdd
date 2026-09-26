"""Code-drawn overlay for the Astra images only (spec §13-§14, canon §84: the next-chunk arrow never goes into the VLA
input). Projection from the robot's own kinematics (tip = kin.tcp_pose) and the camera models (live parent-link pose
x mount, the E-Astra-motion probe's camera_pose), never object ground truth. Head image: tip ring, fading trace
(MolmoAct / PEEK style), pale-green committed-next-motion arrow, yellow-green remaining Astra correction, robot-frame
axes at the tip (plan ruling 4). Wrist images: only a corner box with the same arrows as directions (edges only,
spec §13). polylines(): MolmoAct trace format for the request JSON -- <= 5 points, current point first, 0-255 image
ints.

Colours (controller ruling O2, 2026-09-26, docs/stage3/molmoact_r2_readiness.md C6/M5): the original cyan/magenta
arrows collided with R2's own palette (dr distractor col_cyan, mug_marker o11) and the fading trace's yellow
collided with the o9 box. TRACE_COLOR/NEXT_COLOR/OFFSET_COLOR were chosen (exhaustive RGB grid search over
harvest/sim/randomization_pools.json's distractor_colors + harvest/sim/scene.py OBJ_GEOM's object colours) to each
clear >= 120 RGB units from every one of those ~15 colours -- tests/couple/test_overlay_colours.py checks this
against the live palette, not a hard-coded copy. The 15-colour R2 palette occupies nearly the whole hue wheel, so
the only clear margin left is a narrow pale-green/spring-green/chartreuse band; the three new colours are shades
within that band (mutually 90-146 RGB units apart) rather than fully separate hues, and the two arrows/trace are
still told apart by which vector they follow (committed motion vs. remaining correction) plus the trace's fading
alpha. AXIS_COLORS were left as the conventional red/green/blue (checked, not changed): each does clear < 120 from
one saturated object colour by strict Euclidean distance, but the three short perpendicular lines radiating from the
tip are a distinctive geometric pattern (not a solid colour patch), and departing from the universal x/y/z=r/g/b
convention would cost more legibility than it buys.

Known limitation (controller ruling O1): the tip drawn here is kin.tcp_pose() -- the simulator's own EE pose, exact
in this plan. On the real robot only URDF FK is available (no simulator ground truth), and the E-Astra-motion /
MolmoAct-readiness probe measured URDF FK vs. the simulator's own tip at a median residual of 9.5 mm (~6 px in the
head image, P40 gate G-fk, docs/stage3/molmoact_r2_readiness.md §4.2) -- not a constant offset but a kinematic model
difference. Real-robot deployment must calibrate FK against a measured EE pose before trusting this overlay's tip
placement; that calibration is out of scope for this plan."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

INSET = 64
AXES_M = 0.03
WHITE = (255, 255, 255)
TRACE_COLOR = (120, 255, 85)   # pale green (was yellow -- collided with the o9 box)
NEXT_COLOR = (35, 255, 135)    # spring green (was cyan -- collided with dr col_cyan)
OFFSET_COLOR = (90, 255, 0)    # chartreuse (was magenta -- collided with the o11/mug_marker marker)
AXIS_COLORS = ((255, 40, 40), (40, 220, 40), (60, 120, 255))  # conventional red/green/blue x/y/z; kept, see docstring


@dataclass(frozen=True)
class CamModel:
    K: np.ndarray
    R: np.ndarray
    t: np.ndarray
    W: int
    H: int

    @classmethod
    def from_dict(cls, d: dict) -> "CamModel":
        return cls(np.asarray(d["K"], float), np.asarray(d["R"], float), np.asarray(d["t"], float), int(d["W"]),
                   int(d["H"]))


def project(cam: CamModel, p) -> tuple:
    pc = cam.R.T @ (np.asarray(p, float) - cam.t)
    z = float(pc[2])
    if z <= 1e-9:
        return math.nan, math.nan, z
    return float(cam.K[0, 0] * pc[0] / z + cam.K[0, 2]), float(cam.K[1, 1] * pc[1] / z + cam.K[1, 2]), z


def uv255(cam: CamModel, p):
    u, v, z = project(cam, p)
    if z <= 0 or not math.isfinite(u) or not (0 <= u < cam.W and 0 <= v < cam.H):
        return None
    return [int(round(255 * u / cam.W)), int(round(255 * v / cam.H))]


class EETrace:
    def __init__(self, keep_s: float = 4.0):
        self.keep_s, self.h = keep_s, deque()

    def add(self, t: float, p) -> None:
        self.h.append((float(t), np.asarray(p, float).copy()))
        while self.h and self.h[0][0] < t - self.keep_s - 1e-9:
            self.h.popleft()

    def window(self, now: float, span: float) -> list:
        return [(t, p) for t, p in self.h if t >= now - span - 1e-9]


def _px(cam, p):
    u, v, z = project(cam, p)
    return None if z <= 0 or not math.isfinite(u) else (u, v)


def _arrow(d, a, b, col, width=3):
    d.line([tuple(a), tuple(b)], fill=col + (255,), width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-1, 1):
        e = (b[0] - 8 * math.cos(ang + s * 0.45), b[1] - 8 * math.sin(ang + s * 0.45))
        d.line([tuple(b), e], fill=col + (255,), width=width)


def draw_overlay(img, cam: CamModel, *, tip, trace, next_vec=None, offset_vec=None, wrist: bool = False) -> np.ndarray:
    from PIL import Image, ImageDraw
    base = Image.fromarray(np.asarray(img, np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tip = np.asarray(tip, float)
    arrows = [(v, c) for v, c in ((next_vec, NEXT_COLOR), (offset_vec, OFFSET_COLOR))
              if v is not None and float(np.linalg.norm(v)) > 1e-6]
    if wrist:
        W = base.size[0]
        x0, y0 = W - INSET - 2, 2
        d.rectangle([x0, y0, x0 + INSET, y0 + INSET], fill=(0, 0, 0, 150))
        c = np.array([x0 + INSET / 2, y0 + INSET / 2])
        for v, col in [(AXES_M * e, ac) for e, ac in zip(np.eye(3), AXIS_COLORS)] + arrows:
            dc = cam.R.T @ np.asarray(v, float)
            n = math.hypot(dc[0], dc[1])
            if n > 1e-9:
                _arrow(d, c, c + np.array([dc[0], dc[1]]) / n * (INSET / 2 - 5), col, width=2)
    else:
        pts = [q for q in (_px(cam, p) for p in trace) if q is not None]
        for i in range(1, len(pts)):
            d.line([pts[i - 1], pts[i]], fill=TRACE_COLOR + (int(60 + 160 * i / max(len(pts) - 1, 1)),), width=2)
        pt = _px(cam, tip)
        if pt is not None:
            for e, col in zip(np.eye(3), AXIS_COLORS):
                q = _px(cam, tip + AXES_M * e)
                if q is not None:
                    d.line([pt, q], fill=col + (230,), width=2)
            for v, col in arrows:
                q = _px(cam, tip + np.asarray(v, float))
                if q is not None:
                    _arrow(d, pt, q, col)
            d.ellipse([pt[0] - 6, pt[1] - 6, pt[0] + 6, pt[1] + 6], outline=WHITE + (255,), width=2)
    return np.asarray(Image.alpha_composite(base, layer).convert("RGB"))


def polylines(cams: dict, pts_newest_first: list, n: int = 5) -> dict:
    if not pts_newest_first:
        return {}
    k = len(pts_newest_first)
    idx = sorted({int(round(x)) for x in np.linspace(0, k - 1, min(n, k))})
    out = {}
    for c, cam in cams.items():
        uv = [q for q in (uv255(cam, pts_newest_first[i]) for i in idx) if q is not None]
        if uv:
            out[c] = uv
    return out
