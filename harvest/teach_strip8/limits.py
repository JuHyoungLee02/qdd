"""user-log 171 (docs/stage3/prereg_limits.md): (A) corruption injectors for the D limit map, (B) the depth rescue of the
D point resolver. Pure numpy (the episode wiring is in boost.LimitEpisode).
(A) object_mask (pixels of an object: back-projected within r of its xy centre and above the plane), depth_holes
    (a contiguous fraction f of the mask set to 0 = transparent / reflective surface), depth_noise (teach_l8d zed_mini
    stereo noise with sigma_d scaled k x), lighting (gain + colour tint levels), occlude (a grey box over a fraction of
    the target's image box; RGB only).
(B) rescue_resolve: when more than HOLE_FRAC of the depth pixels in a window around the pointed pixel are missing:
    1 masked_median - fill the missing window pixels with the median depth of the valid above-plane pixels in the
    window (needs >= MIN_OBJ_PX); 2 fill - neighbour (3x3 nan-median) fill of a larger window, trusted only when the
    point then lands on an object; 3 memory - the missing pixels from the remembered depth (boost1b render);
    4 remeasure - no target (the executor re-observes from another pose)."""
from __future__ import annotations

import numpy as np

from ..astra_solo import resolve as RS

HOLE_FRAC = 0.30
WIN_PX = 12
FILL_WIN_PX = 30
FILL_ITERS = 12
MIN_OBJ_PX = 20
LIGHT_LEVELS = ("dim_warm", "bright_cool", "dark_green")
_LIGHT = {"dim_warm": (0.55, (18, 4, -18)), "bright_cool": (1.5, (-15, 0, 20)), "dark_green": (0.7, (-20, 25, -20))}


def object_mask(cam, depth, plane, xy, r=0.06, h_min=0.005) -> np.ndarray:
    P = RS.depth_points(cam, depth)
    d = np.hypot(P[..., 0] - xy[0], P[..., 1] - xy[1])
    return np.isfinite(d) & (d <= r) & (P[..., 2] - plane > h_min)


def depth_holes(depth, mask, frac: float, seed: int = 0) -> np.ndarray:
    out = np.array(depth, float, copy=True)
    ys, xs = np.nonzero(mask)
    if not len(ys) or frac <= 0:
        return out
    a = np.random.default_rng([int(seed), 171]).uniform(0, 2 * np.pi)
    key = xs * np.cos(a) + ys * np.sin(a)
    k = int(round(frac * len(ys)))
    sel = np.argsort(key, kind="stable")[:k]
    out[ys[sel], xs[sel]] = 0.0
    return out


def depth_noise(depth, rgb, fx: float, k: float, seed: int = 0) -> np.ndarray:
    from ..teach_l8d.depth_noise import PRESETS, stereo_noise
    d, _ = stereo_noise(depth, rgb, fx, "zed_mini", seed=seed, sigma_d_px=PRESETS["zed_mini"]["sigma_d_px"] * k)
    return d


def lighting(rgb, level: str, seed: int = 0) -> np.ndarray:
    g, tint = _LIGHT[level]
    x = np.asarray(rgb, float)[..., :3] * g + np.asarray(tint, float)
    return np.clip(x, 0, 255).astype(np.uint8)


def occlude(rgb, mask, frac: float, seed: int = 0) -> np.ndarray:
    out = np.array(rgb, copy=True)
    ys, xs = np.nonzero(mask)
    if not len(ys) or frac <= 0:
        return out
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rng = np.random.default_rng([int(seed), 172])
    w = max(1, int(round((x1 - x0) * frac)))
    left = rng.random() < 0.5
    xa, xb = (x0, x0 + w) if left else (x1 - w, x1)
    out[y0:y1, xa:xb, :3] = (90, 90, 90)
    return out


def _hole_frac(depth, iu, iv, win) -> float:
    z = np.asarray(depth, float)[max(iv - win, 0):iv + win + 1, max(iu - win, 0):iu + win + 1]
    return float(1.0 - (np.isfinite(z) & (z > 0)).mean()) if z.size else 1.0


def _nan_fill(z, iters):
    z = np.where(np.isfinite(z) & (z > 0), z, np.nan)
    for _ in range(iters):
        miss = np.isnan(z)
        if not miss.any():
            break
        pad = np.pad(z, 1, constant_values=np.nan)
        H, W = z.shape
        stack = np.stack([pad[1 + dy:1 + dy + H, 1 + dx:1 + dx + W] for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
        import warnings
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            med = np.nanmedian(stack, 0)
        z = np.where(miss, med, z)
    return z


_RP0 = RS.resolve_point  # the original resolver (LimitEpisode may patch RS.resolve_point with v2)
NEAR_PCT = 20  # real RB2 (작전T rb2_dtest3): near-depth 20th percentile inside the object mask
CONT_DROP_M = 0.02  # a region whose centre is this much below its rim is a container (opening)


def resolve_point_v2(cam, depth, prior_z, point_2d, tcp=None) -> dict:
    """resolve.resolve_point with two changes (prereg_limits.md change 1): the object's (x, y) = the mask centroid
    pixel back-projected at the NEAR_PCT-th percentile of the mask's z-depth (instead of the top-band mean), and a
    container (centre > CONT_DROP_M below the rim) gets the opening centre (bbox centre of the rim band) with the rim
    height as its top."""
    from ..astra_motion.geometry import PIX_C
    r = _RP0(cam, depth, prior_z, point_2d, tcp=tcp)
    if r["kind"] != "object":
        return dict(r, method="v2")
    P = RS.depth_points(cam, depth)
    plane = r["plane"]
    hgt = P[..., 2] - plane
    above = np.isfinite(hgt) & (hgt > RS.H_MIN) & ~RS.robot_mask(hgt, plane, tcp)
    reg = RS._region(P, above, (r["seed"][1], r["seed"][0]))
    top_h = float(np.percentile(hgt[reg], 95))
    band = reg & (hgt >= top_h - RS.TOP_BAND_M)
    bxy = P[band][:, :2]
    c = (bxy.min(0) + bxy.max(0)) / 2
    rad = float(np.linalg.norm(bxy.max(0) - bxy.min(0))) / 4
    inner = np.isfinite(hgt) & (np.hypot(P[..., 0] - c[0], P[..., 1] - c[1]) < rad)  # floor may be below H_MIN
    if inner.sum() >= MIN_OBJ_PX and float(np.median(hgt[inner])) < top_h - CONT_DROP_M:
        return dict(r, xy=[round(float(c[0]), 4), round(float(c[1]), 4)], method="v2_container")
    vv, uu = np.nonzero(reg)
    z = np.asarray(depth, float)[reg]
    z20 = float(np.percentile(z[np.isfinite(z) & (z > 0)], NEAR_PCT))
    u, v = uu.mean() + PIX_C, vv.mean() + PIX_C
    p = np.asarray(cam.R, float) @ np.array([(u - cam.cx) / cam.fx * z20, (v - cam.cy) / cam.fy * z20, z20]) \
        + np.asarray(cam.t, float)
    return dict(r, xy=[round(float(p[0]), 4), round(float(p[1]), 4)], method="v2_near20")


def rescue_resolve(cam, depth, prior_z, point_2d, tcp=None, memory=None) -> dict:
    iu, iv = RS.to_pixel(point_2d, cam.W, cam.H)
    hf = _hole_frac(depth, iu, iv, WIN_PX)
    if hf <= HOLE_FRAC:
        return dict(RS.resolve_point(cam, depth, prior_z, point_2d, tcp=tcp), rescue="none", hole_frac=round(hf, 3))
    z = np.array(depth, float, copy=True)
    r0, r1, c0, c1 = max(iv - WIN_PX, 0), iv + WIN_PX + 1, max(iu - WIN_PX, 0), iu + WIN_PX + 1
    P = RS.depth_points(cam, z)
    plane = RS.table_plane(P, prior_z)
    hgt = P[..., 2] - plane
    win = (slice(r0, r1), slice(c0, c1))
    above = np.isfinite(hgt[win]) & (hgt[win] > RS.H_MIN) & ~RS.robot_mask(hgt[win], plane, tcp)
    # 1 masked median: the valid object pixels left in the window stand for the missing ones
    if above.sum() >= MIN_OBJ_PX:
        from ..astra_motion.geometry import PIX_C
        zw = z[win]
        miss = ~(np.isfinite(zw) & (zw > 0))
        ztop = plane + float(np.median(hgt[win][above]))  # the missing pixels lie on the object's median height
        vv, uu = np.nonzero(miss)
        d = np.stack([(uu + c0 + PIX_C - cam.cx) / cam.fx, (vv + r0 + PIX_C - cam.cy) / cam.fy, np.ones(len(uu))], -1)
        dz = d @ np.asarray(cam.R, float)[2]
        with np.errstate(all="ignore"):
            zw[vv, uu] = np.where(dz < 0, (ztop - float(cam.t[2])) / dz, np.nan)
        r = RS.resolve_point(cam, z, prior_z, point_2d, tcp=tcp)
        if r["kind"] == "object":
            return dict(r, rescue="masked_median", hole_frac=round(hf, 3))
    # 2 neighbour fill of a larger window, trusted only if the point then lands on an object
    # (object pixels only propagate: a table neighbour would fake an object in front of the table)
    z2 = np.array(depth, float, copy=True)
    fw = (slice(max(iv - FILL_WIN_PX, 0), iv + FILL_WIN_PX + 1), slice(max(iu - FILL_WIN_PX, 0), iu + FILL_WIN_PX + 1))
    hw = hgt[fw]
    obj = np.isfinite(hw) & (hw > RS.H_MIN) & ~RS.robot_mask(hw, plane, tcp)
    if obj.sum() >= MIN_OBJ_PX // 2:
        zf = z2[fw]
        miss = ~(np.isfinite(zf) & (zf > 0))
        prop = _nan_fill(np.where(obj, zf, np.nan), FILL_ITERS)
        zf[miss] = np.nan_to_num(prop[miss], nan=0.0)
        r = RS.resolve_point(cam, z2, prior_z, point_2d, tcp=tcp)
        if r["kind"] == "object":
            return dict(r, rescue="fill", hole_frac=round(hf, 3))
    # 3 memory (the remembered depth rendered into this camera)
    if memory is not None:
        m = np.asarray(memory, float)
        z3 = np.array(depth, float, copy=True)
        miss = ~(np.isfinite(z3) & (z3 > 0)) & np.isfinite(m) & (m > 0)
        z3[miss] = m[miss]
        r = RS.resolve_point(cam, z3, prior_z, point_2d, tcp=tcp)
        if r["kind"] == "object":
            return dict(r, rescue="memory", hole_frac=round(hf, 3))
    # 4 remeasure
    return {"kind": "remeasure", "goal": None, "rescue": "remeasure", "hole_frac": round(hf, 3), "pixel": [iu, iv]}
