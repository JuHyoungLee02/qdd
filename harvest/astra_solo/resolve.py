"""Point-then-act resolver of the astra-solo-pt interface (canon §97 보충 2): a pixel the model POINTS at in the head image
+ a height intent -> a robot-frame TCP target, computed by code from the head camera's z-depth map
(`distance_to_image_plane`) and its calibration, never by the model. Pure numpy (tests and the pod share it).

Steps
1. table plane: the median height of the depth points within +-3 cm of the prior table height (canon §97: the plane is
   measured; the sim prior is env.table_top_z). Reported next to the prior.
2. the pointed pixel (0-1000 scale of image 1 -> pixel index). If it is not on something standing on the table
   (height above the plane <= H_MIN), the nearest such pixel within SNAP_PX is used instead ('snapped'); with none,
   the point is a TABLE point (target xy = where the pixel ray meets the plane).
3. the object = the 4-connected region of pixels above the plane (> H_MIN) around the seed whose neighbouring 3-D
   points are closer than EDGE_M (depth edges split touching silhouettes). top = 95th percentile height of the region;
   centre xy = mean xy of the region's points within TOP_BAND_M of the top (the flat top face of the scene's
   primitives seen from above; for a held or partly hidden object this is the visible top only).
4. height intent -> TCP z (the prompt's grasp / place recipe, from the measured heights):
   above  top + 0.08 (+ the held object's grip offset when an object is held: its bottom 8 cm above the top)
   grasp  top - GRASP_BELOW_TOP_M (the pads around the upper part)
   place  top + grip offset + PLACE_CLEAR_M (the held object's bottom 1 cm above the pointed surface)
   lift   plane + CARRY_DZ at the current TCP xy (no point needed)
   grip offset = TCP height above the plane when the gripper last closed on something (measured by the episode);
   unknown -> the place target is top + PLACE_FALLBACK_M (reported).
The workspace box clips the result later (the executor), reported like any clip."""
from __future__ import annotations

import math

import numpy as np

from ..astra_motion.geometry import PIX_C, lift_plane

H_MIN = 0.008  # m above the plane: an object pixel
SNAP_PX = 12  # px radius searched for an object pixel when the point lands just beside one
EDGE_M = 0.015  # m: neighbouring 3-D points farther apart are not the same surface
TOP_BAND_M = 0.005
PLANE_WIN_M = 0.03
ABOVE_DZ = 0.08  # TCP above the top (= the v2 truth: grasp point + 10 cm = top + 8.2 cm)
GRASP_BELOW_TOP_M = 0.02  # the prompt's recipe ("z = table + h - 0.02")
PLACE_CLEAR_M = 0.01  # the prompt's recipe (bottom about 1 cm above the target surface)
PLACE_FALLBACK_M = 0.12
CARRY_DZ = 0.22  # = teach_l8.labels.CARRY_DZ
INTENTS = ("above", "grasp", "place", "lift")
SCALE = 1000.0


def to_pixel(point_2d, W: int, H: int) -> tuple:
    """0-1000 image coordinates (x right, y down; 0 = left / top edge, 1000 = right / bottom edge) -> integer pixel
    index (clamped into the image)."""
    x, y = float(point_2d[0]), float(point_2d[1])
    iu = int(min(max(math.floor(x / SCALE * W), 0), W - 1))
    iv = int(min(max(math.floor(y / SCALE * H), 0), H - 1))
    return iu, iv


def to_scaled(u: float, v: float, W: int, H: int) -> list:
    """Continuous image coordinates (pixel centre of index i = i + 0.5) -> the 0-1000 scale (rounded integers)."""
    return [int(round(u / W * SCALE)), int(round(v / H * SCALE))]


def depth_points(cam, depth: np.ndarray) -> np.ndarray:
    """z-depth map (H, W) -> base-frame points (H, W, 3); invalid depths (0, inf, nan) give nan points."""
    z = np.asarray(depth, float)
    z = np.where(np.isfinite(z) & (z > 0), z, np.nan)
    iu, iv = np.meshgrid(np.arange(cam.W) + PIX_C, np.arange(cam.H) + PIX_C)
    pc = np.stack([(iu - cam.cx) / cam.fx * z, (iv - cam.cy) / cam.fy * z, z], -1)
    return pc @ np.asarray(cam.R, float).T + np.asarray(cam.t, float)


def table_plane(P: np.ndarray, prior_z: float) -> float:
    z = P[..., 2]
    m = np.isfinite(z) & (np.abs(z - prior_z) <= PLANE_WIN_M)
    return float(np.median(z[m])) if m.any() else float(prior_z)


def _region(P: np.ndarray, above: np.ndarray, seed: tuple) -> np.ndarray:
    """4-connected region of `above` pixels around seed (row, col) whose neighbouring points are < EDGE_M apart."""
    ok_r = above[:, :-1] & above[:, 1:] & (np.linalg.norm(P[:, :-1] - P[:, 1:], axis=-1) < EDGE_M)
    ok_d = above[:-1, :] & above[1:, :] & (np.linalg.norm(P[:-1, :] - P[1:, :], axis=-1) < EDGE_M)
    cur = np.zeros(above.shape, bool)
    cur[seed] = True
    while True:
        nxt = cur.copy()
        nxt[:, 1:] |= cur[:, :-1] & ok_r
        nxt[:, :-1] |= cur[:, 1:] & ok_r
        nxt[1:, :] |= cur[:-1, :] & ok_d
        nxt[:-1, :] |= cur[1:, :] & ok_d
        if (nxt == cur).all():
            return cur
        cur = nxt


def resolve_point(cam, depth: np.ndarray, prior_z: float, point_2d) -> dict:
    """-> {"kind": "object" | "table", "xy": [x, y], "top": z, "plane": z, "pixel": [iu, iv], "seed": [iu, iv],
    "snapped": bool, "n_px": int}."""
    P = depth_points(cam, depth)
    plane = table_plane(P, prior_z)
    hgt = P[..., 2] - plane
    above = np.isfinite(hgt) & (hgt > H_MIN)
    iu, iv = to_pixel(point_2d, cam.W, cam.H)
    seed, snapped = (iv, iu), False
    if not above[iv, iu]:
        r0, r1 = max(0, iv - SNAP_PX), min(cam.H, iv + SNAP_PX + 1)
        c0, c1 = max(0, iu - SNAP_PX), min(cam.W, iu + SNAP_PX + 1)
        rr, cc = np.nonzero(above[r0:r1, c0:c1])
        if rr.size:
            d2 = (rr + r0 - iv) ** 2 + (cc + c0 - iu) ** 2
            k = int(np.argmin(d2))
            if d2[k] <= SNAP_PX ** 2:
                seed, snapped = (int(rr[k] + r0), int(cc[k] + c0)), True
    out = {"plane": round(plane, 4), "pixel": [iu, iv], "seed": [seed[1], seed[0]], "snapped": snapped}
    if not above[seed]:
        q = lift_plane(cam, iu, iv, plane)
        if q is None:
            return dict(out, kind="none", xy=None, top=None, n_px=0)
        return dict(out, kind="table", xy=[round(float(q[0]), 4), round(float(q[1]), 4)], top=round(plane, 4),
                    n_px=0)
    reg = _region(P, above, seed)
    h = hgt[reg]
    top_h = float(np.percentile(h, 95))
    band = reg & (hgt >= top_h - TOP_BAND_M)
    xy = P[band][:, :2].mean(0)
    return dict(out, kind="object", xy=[round(float(xy[0]), 4), round(float(xy[1]), 4)],
                top=round(plane + top_h, 4), n_px=int(reg.sum()))


def target_of(intent: str, res: dict | None, plane: float, tcp, holding: bool, grip_offset: float | None) -> tuple:
    """(TCP target [x, y, z], notes list) for a height intent and a resolved point (res may be None for lift)."""
    tcp = np.asarray(tcp, float)
    notes = []
    if intent == "lift":
        return [float(tcp[0]), float(tcp[1]), plane + CARRY_DZ], notes
    x, y = res["xy"]
    top = float(res["top"])
    if intent == "above":
        z = top + ABOVE_DZ + (grip_offset if (holding and grip_offset is not None) else 0.0)
        if holding and grip_offset is None:
            z, _ = top + ABOVE_DZ + PLACE_FALLBACK_M, notes.append("grip_offset_unknown")
    elif intent == "grasp":
        z = top - GRASP_BELOW_TOP_M
    elif intent == "place":
        if grip_offset is None:
            z, _ = top + PLACE_FALLBACK_M, notes.append("grip_offset_unknown")
        else:
            z = top + grip_offset + PLACE_CLEAR_M
    else:
        raise ValueError(intent)
    return [float(x), float(y), float(z)], notes
