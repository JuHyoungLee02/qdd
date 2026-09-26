"""Code-drawn overlay for the Astra images only (spec §13-§14, canon §84: the next-chunk arrow never goes into the VLA
input). Projection from the robot's own kinematics (tip = kin.tcp_pose, the pad-centre TCP the planner/IK actually
commands) and the camera models (live parent-link pose x mount, the E-Astra-motion probe's camera_pose), never
object ground truth. Head image: tip ring, fading trace (MolmoAct / PEEK style), committed-next-motion arrow,
remaining-Astra-correction arrow, robot-frame axes at the tip (plan ruling 4). Wrist images: only a corner box with
the same arrows as directions (edges only, spec §13). polylines(): MolmoAct trace format for the request JSON --
<= 5 points, current point first, 0-255 image ints.

Colours + patterns (controller rulings O2/O2b, 2026-09-26, docs/stage3/molmoact_r2_readiness.md C6/M5): in the HEAD
image the original cyan/magenta arrows collided with R2's own palette (dr distractor col_cyan, the o11/mug_marker
marker) and the fading trace's yellow collided with the o9 box. TRACE_COLOR/NEXT_COLOR/OFFSET_COLOR were chosen
(exhaustive RGB grid search over harvest/sim/randomization_pools.json's distractor_colors, 9 across the test+train
pools, + harvest/sim/scene.py OBJ_GEOM's 6 object colours -- 15 total) to each clear >= 120 RGB units from every one
of those 15 -- tests/couple/test_overlay_colours.py checks this against the live palette, not a hard-coded copy.
That 15-colour palette occupies nearly the whole hue wheel, so the only clear margin left is a narrow
pale-green/spring-green/chartreuse band (all three new colours sit there, hues roughly 99-147 degrees) -- too close
in HUE alone to tell the two arrows apart reliably (O2b review finding), so in the head image they are additionally
told apart by PATTERN, not colour: the next-motion arrow is solid, thick, with a filled head; the offset/correction
arrow is dashed, thinner, with an open head; the fading trace is a thin outlined line; axis lines are thin with no
arrowhead at all (unlike the two arrows). Every head-image stroke gets a 1 px black outline for contrast against
any background. AXIS_COLORS stay the conventional red/green/blue (axis-y's green does sit inside the arrows' hue
band, but "thin, no arrowhead, outlined" already separates axes from arrows by shape, so the colour was kept for
the universal x/y/z=r/g/b convention). In the WRIST corner box the palette-collision rule does not apply (opaque
dark background, not a view of the R2 scene's own colours), so WRIST_NEXT_COLOR/WRIST_OFFSET_COLOR go back to
clearly distinct, vivid hues (cyan/magenta); wrist axes are drawn the same way as head axes (thin lines, no
arrowhead) so the three glyphs in that small box are not all identical arrow shapes (the earlier O2b review finding
was exactly this: axes + both arrows all drawn as the same `_arrow` glyph from the same centre).

Known limitation -- EE source (controller ruling O1, corrected by O1b review 2026-09-26): the tip drawn here is
kin.tcp_pose() = OraclePlanner.tcp_pose() = env.ee_pose() + env.tcp_offset -- the PAD-CENTRE TCP the planner/IK
actually targets (harvest/sim/scene.py _measure_finger_offsets: "(pad centre, fingertip) distance from the link7
origin"). This is a DIFFERENT point from env.finger_mid() (the two finger-link-2 midpoint), which is what R2's own
recorded "tcp" label uses (harvest/datagen/gen.py, harvest/sim/oracle_state.py) and what the MolmoAct-readiness
agent's G-fk gate actually compared URDF FK against (docs/stage3/molmoact_r2_readiness.md §4.2 -- NOT the
E-Astra-motion probe, and NOT P40: P40 is the unrelated camera pos_w/quat_w staleness defect). Pad-centre TCP and
finger_mid differ by ~7.8 mm in this scene (docs/stage3/results/r5_closed_loop.md, the mock_full1/mock_full2 rows).
This overlay intentionally draws the pad-centre TCP (not finger_mid): it is the point Astra's edits actually move
via IK, and R2-label parity is not needed here because no VLA overlay/trace conditioning is in use in this plan
(E-MA2 was NONE; the MolmoAct E-MA1 trace-conditioning option was not adopted). On the real robot only URDF FK is
available (no simulator ground truth for either point); before trusting this overlay's tip on hardware, FK must be
calibrated against a measured pad-centre EE pose specifically (not against finger_mid) -- that calibration is out
of scope for this plan."""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

INSET = 64
AXES_M = 0.03
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TRACE_COLOR = (120, 255, 85)   # pale green (was yellow -- collided with the o9 box); head image only
NEXT_COLOR = (35, 255, 135)    # spring green (was cyan -- collided with dr col_cyan); head image, solid/filled head
OFFSET_COLOR = (90, 255, 0)    # chartreuse (was magenta -- collided with o11/mug_marker); head image, dashed/open head
AXIS_COLORS = ((255, 40, 40), (40, 220, 40), (60, 120, 255))  # conventional red/green/blue x/y/z; thin, no head
WRIST_NEXT_COLOR = (0, 255, 255)     # cyan -- wrist corner box only (opaque background, palette rule N/A)
WRIST_OFFSET_COLOR = (255, 0, 255)   # magenta -- wrist corner box only


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


def _dash_segments(a, b, dash=7.0, gap=5.0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    length = float(np.linalg.norm(b - a))
    if length < 1e-6:
        return []
    unit, segs, s = (b - a) / length, [], 0.0
    while s < length:
        e = min(s + dash, length)
        segs.append((tuple(a + unit * s), tuple(a + unit * e)))
        s += dash + gap
    return segs


def _stroke(d, a, b, col, width, *, dashed=False, outline=True):
    """A line (optionally dashed) with an optional 1 px black outline (controller ruling O2b)."""
    for p0, p1 in (_dash_segments(a, b) if dashed else [(tuple(a), tuple(b))]):
        if outline:
            d.line([p0, p1], fill=BLACK + (255,), width=width + 2)
        d.line([p0, p1], fill=col + (255,), width=width)


def _head(d, tip, ang, col, *, filled, size=9, spread=0.5, outline=True):
    """Filled (solid triangle) or open (two short strokes) arrowhead -- the two styles are visually distinct even
    when the shaft colour alone would not be (O2b: next=filled, offset=open)."""
    p1 = (tip[0] - size * math.cos(ang - spread), tip[1] - size * math.sin(ang - spread))
    p2 = (tip[0] - size * math.cos(ang + spread), tip[1] - size * math.sin(ang + spread))
    if filled:
        if outline:
            g = size + 2
            b1 = (tip[0] - g * math.cos(ang - spread), tip[1] - g * math.sin(ang - spread))
            b2 = (tip[0] - g * math.cos(ang + spread), tip[1] - g * math.sin(ang + spread))
            d.polygon([tuple(tip), b1, b2], fill=BLACK + (255,))
        d.polygon([tuple(tip), p1, p2], fill=col + (255,))
    else:
        for e in (p1, p2):
            if outline:
                d.line([tuple(tip), e], fill=BLACK + (255,), width=3)
            d.line([tuple(tip), e], fill=col + (255,), width=1)


def _arrow(d, a, b, col, *, width, dashed=False, filled_head=True, head_size=9):
    a, b = np.asarray(a, float), np.asarray(b, float)
    _stroke(d, a, b, col, width, dashed=dashed)
    _head(d, b, math.atan2(b[1] - a[1], b[0] - a[0]), col, filled=filled_head, size=head_size)


def _axis_line(d, a, b, col, width=1):
    """Thin, outlined, NO arrowhead -- the shape (not just colour) that tells an axis from an arrow (O2b)."""
    _stroke(d, a, b, col, width, dashed=False)


def draw_overlay(img, cam: CamModel, *, tip, trace, next_vec=None, offset_vec=None, wrist: bool = False) -> np.ndarray:
    from PIL import Image, ImageDraw
    base = Image.fromarray(np.asarray(img, np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tip = np.asarray(tip, float)
    if wrist:
        arrows = [(v, c, s) for v, c, s in ((next_vec, WRIST_NEXT_COLOR, "next"), (offset_vec, WRIST_OFFSET_COLOR, "offset"))
                  if v is not None and float(np.linalg.norm(v)) > 1e-6]
        W = base.size[0]
        x0, y0 = W - INSET - 2, 2
        d.rectangle([x0, y0, x0 + INSET, y0 + INSET], fill=(0, 0, 0, 150))
        c = np.array([x0 + INSET / 2, y0 + INSET / 2])
        reach = INSET / 2 - 5
        for e, col in zip(np.eye(3), AXIS_COLORS):
            dc = cam.R.T @ (AXES_M * e)
            n = math.hypot(dc[0], dc[1])
            if n > 1e-9:
                _axis_line(d, c, c + np.array([dc[0], dc[1]]) / n * reach, col, width=1)
        for v, col, style in arrows:
            dc = cam.R.T @ np.asarray(v, float)
            n = math.hypot(dc[0], dc[1])
            if n > 1e-9:
                end = c + np.array([dc[0], dc[1]]) / n * reach
                _arrow(d, c, end, col, width=3 if style == "next" else 2, dashed=(style == "offset"),
                      filled_head=(style == "next"), head_size=6 if style == "next" else 4)
    else:
        arrows = [(v, c, s) for v, c, s in ((next_vec, NEXT_COLOR, "next"), (offset_vec, OFFSET_COLOR, "offset"))
                  if v is not None and float(np.linalg.norm(v)) > 1e-6]
        pts = [q for q in (_px(cam, p) for p in trace) if q is not None]
        for i in range(1, len(pts)):
            a = int(60 + 160 * i / max(len(pts) - 1, 1))
            d.line([pts[i - 1], pts[i]], fill=BLACK + (a,), width=4)
            d.line([pts[i - 1], pts[i]], fill=TRACE_COLOR + (a,), width=2)
        pt = _px(cam, tip)
        if pt is not None:
            for e, col in zip(np.eye(3), AXIS_COLORS):
                q = _px(cam, tip + AXES_M * e)
                if q is not None:
                    _axis_line(d, pt, q, col, width=1)
            for v, col, style in arrows:
                q = _px(cam, tip + np.asarray(v, float))
                if q is not None:
                    _arrow(d, pt, q, col, width=4 if style == "next" else 2, dashed=(style == "offset"),
                          filled_head=(style == "next"), head_size=10 if style == "next" else 6)
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


def _nz(v) -> bool:
    return v is not None and float(np.linalg.norm(v)) > 1e-6


def drawn_elements(models: dict, *, tip, trace, next_vec=None, offset_vec=None, axisguide=()) -> dict | None:
    """What draw_overlay puts on the images (astra-couple@v2 legend: only the elements actually drawn, prompt health
    F2), in the shape of prompt_v2.legend_text: {"head": LEGEND keys, "wrist": WRIST_ARROW keys or None when no wrist
    image carries an overlay, "axisguide": cameras with the axis guide}; None when no image carries an overlay.
    Head keys follow tools/eacc/arms.images: ring / axes / next / offset only with the tip inside the head image,
    trace with >= 2 projected trace points."""
    if not models:
        return None
    head = set()
    m = models.get("cam_head")
    if m is not None:
        pt = _px(m, tip)
        if pt is not None and 0 <= pt[0] < m.W and 0 <= pt[1] < m.H:
            head |= {"ring", "axes"} | ({"next"} if _nz(next_vec) else set()) | ({"offset"} if _nz(offset_vec)
                                                                                  else set())
        if sum(_px(m, p) is not None for p in trace) >= 2:
            head.add("trace")
    wrist = None
    if any(c != "cam_head" for c in models):
        wrist = {k for k, v in (("next", next_vec), ("offset", offset_vec)) if _nz(v)}
    return {"head": head, "wrist": wrist, "axisguide": sorted(axisguide)}


AXIS_LONG_M = 0.10


def draw_axisguide(img, cam: CamModel, tip) -> tuple:
    """Port of tools/eacc/arms.draw_axisguide (E-ACC arm 'ax', prereg change 4; astra-couple@v2 option, off by
    default): AxisGuide-style (RSS 2026, arXiv 2606.06761) robot-frame axes at the projected tip, 10 cm arrows along
    +x / +y / +z labelled '+x' / '+y' / '+z' (outlined), from robot kinematics and the camera model only. Returns
    (image, drawn?) -- nothing is drawn when the tip is outside the image."""
    from PIL import Image, ImageDraw
    pt = _px(cam, tip)
    if pt is None or not (0 <= pt[0] < cam.W and 0 <= pt[1] < cam.H):
        return img, False
    base = Image.fromarray(np.asarray(img, np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=16)
    except (TypeError, OSError):  # older Pillow: bitmap default font
        font = None
    for e, col, lab in zip(np.eye(3), AXIS_COLORS, ("+x", "+y", "+z")):
        q = _px(cam, np.asarray(tip, float) + AXIS_LONG_M * e)
        if q is None:
            continue
        _arrow(d, pt, q, col, width=3, head_size=9)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            d.text((q[0] + 4 + dx, q[1] - 9 + dy), lab, fill=(0, 0, 0, 255), font=font)
        d.text((q[0] + 4, q[1] - 9), lab, fill=col + (255,), font=font)
    return np.asarray(Image.alpha_composite(base, layer).convert("RGB")), True
