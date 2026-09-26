"""MolmoAct-on-R2 readiness gates: pure helpers (numpy only, no Isaac, no torch).

Used by tools/mar2/mar2_gates.py (pod runner) and tests/test_mar2_lib.py. Definitions follow the gate spec in
docs/stage3/molmoact_r2_readiness.md (fixed 2026-09-26T02:35:47Z, before any measurement).

MolmoAct references (arXiv 2508.07917 v4 §3.1; allenai/molmoact@a5cf980):
  preprocess processors.Trace.subsample_to_line   -> molmo_subsample (same semantics, re-implemented)
  olmo/data/image_preprocessor.load_image         -> to_u255 is the inverse of its 0..255 -> pixel mapping,
                                                     draw style (0, 255, 255) RGB, 2 px, anti-aliased polyline
"""
from __future__ import annotations

import math

import numpy as np

# ------------------------------------------------------------------------------------------ MolmoAct trace
def molmo_subsample(points, k: int = 5, fallback=None) -> list:
    """processors.Trace.subsample_to_line: drop None, <= k points kept as is, else k evenly spaced (np.linspace
    int indices, first and last included); no valid point -> [fallback] or []."""
    valid = [p for p in points if p is not None]
    m = len(valid)
    if m == 0:
        return [fallback] if fallback is not None else []
    if m <= k:
        return list(valid)
    idx = np.linspace(0, m - 1, num=k, dtype=int)
    return [valid[j] for j in idx]


def to_u255(u: float, v: float, W: int, H: int) -> list:
    """Continuous pixel coordinate (pixel c covers [c, c+1)) -> MolmoAct 0..255 integers. Inverse of
    load_image: pixel index = q * (W - 1) / 255, pixel centre = index + 0.5."""
    qu = int(round((u - 0.5) * 255.0 / (W - 1)))
    qv = int(round((v - 0.5) * 255.0 / (H - 1)))
    return [min(max(qu, 0), 255), min(max(qv, 0), 255)]


def from_u255(q, W: int, H: int) -> tuple:
    """0..255 integers -> continuous pixel coordinate of the drawn point (pixel centre)."""
    return q[0] * (W - 1) / 255.0 + 0.5, q[1] * (H - 1) / 255.0 + 0.5


def in_image(u: float, v: float, W: int, H: int) -> bool:
    return 0.0 <= u < W and 0.0 <= v < H


def trace_labels(uv, W: int, H: int, k: int = 5) -> list:
    """Per frame t: MolmoAct trace over frames t..end (episode end). uv (N, 2) continuous pixel coordinates of the
    end-effector point; points outside the image are None (pointing failure analogue) and are dropped."""
    pts = [to_u255(u, v, W, H) if (np.isfinite(u) and np.isfinite(v) and in_image(u, v, W, H)) else None
           for u, v in np.asarray(uv, float)]
    return [molmo_subsample(pts[t:], k, fallback=pts[t]) for t in range(len(pts))]


# ------------------------------------------------------------------------------------------ geometry
def quat_to_R(q) -> np.ndarray:
    w, x, y, z = (float(v) for v in q)
    n = w * w + x * x + y * y + z * z
    s = 2.0 / n
    return np.array([[1 - s * (y * y + z * z), s * (x * y - z * w), s * (x * z + y * w)],
                     [s * (x * y + z * w), 1 - s * (x * x + z * z), s * (y * z - x * w)],
                     [s * (x * z - y * w), s * (y * z + x * w), 1 - s * (x * x + y * y)]])


def project(P, K: dict, p, R) -> np.ndarray:
    """perception.geom.project (Isaac camera convention +X optical, +Y left, +Z up): world (N, 3) -> (N, 3) =
    (u, v, depth)."""
    Pc = (np.atleast_2d(np.asarray(P, float)) - np.asarray(p, float)) @ np.asarray(R, float)
    d = Pc[:, 0]
    return np.stack([K["cx"] - K["fx"] * Pc[:, 1] / d, K["cy"] - K["fy"] * Pc[:, 2] / d, d], 1)


def cylinder_points(center, quat, radius: float, height: float, n: int = 96) -> np.ndarray:
    """World points on both rims of a cylinder (axis = local z)."""
    a = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    ring = np.stack([radius * np.cos(a), radius * np.sin(a), np.zeros(n)], 1)
    loc = np.concatenate([ring + [0, 0, height / 2], ring - [0, 0, height / 2]])
    return loc @ quat_to_R(quat).T + np.asarray(center, float)


def cuboid_points(center, quat, size) -> np.ndarray:
    sx, sy, sz = (s / 2 for s in size)
    loc = np.array([[i * sx, j * sy, k * sz] for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)], float)
    return loc @ quat_to_R(quat).T + np.asarray(center, float)


def convex_hull(pts) -> np.ndarray:
    """Andrew monotone chain, counter-clockwise in (u, v) coordinates, (M, 2)."""
    P = sorted(set((float(x), float(y)) for x, y in np.asarray(pts, float)))
    if len(P) <= 2:
        return np.array(P)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return np.array(lo[:-1] + hi[:-1])


def raster_convex(poly, W: int, H: int) -> np.ndarray:
    """Boolean (H, W) mask of pixels whose centre lies inside the convex polygon (counter-clockwise)."""
    poly = np.asarray(poly, float)
    mask = np.zeros((H, W), bool)
    if len(poly) < 3:
        return mask
    u0, v0 = np.floor(poly.min(0)).astype(int)
    u1, v1 = np.ceil(poly.max(0)).astype(int)
    u0, v0, u1, v1 = max(u0, 0), max(v0, 0), min(u1, W), min(v1, H)
    if u0 >= u1 or v0 >= v1:
        return mask
    cu, cv = np.meshgrid(np.arange(u0, u1) + 0.5, np.arange(v0, v1) + 0.5)
    ok = np.ones_like(cu, bool)
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ok &= (b[0] - a[0]) * (cv - a[1]) - (b[1] - a[1]) * (cu - a[0]) >= 0
    mask[v0:v1, u0:u1] = ok
    return mask


def mask_centroid(mask) -> tuple:
    r, c = np.nonzero(mask)
    if len(r) == 0:
        return (math.nan, math.nan)
    return float(c.mean() + 0.5), float(r.mean() + 0.5)


def iou(a, b) -> float:
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else math.nan


# ------------------------------------------------------------------------------------------ colour
def rgb_to_hsv(img) -> tuple:
    """uint8 (H, W, 3) -> hue degrees [0, 360), saturation [0, 1], value [0, 1]."""
    x = np.asarray(img, float) / 255.0
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    mx, mn = x.max(-1), x.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-9
    rm = nz & (mx == r)
    gm = nz & (mx == g) & ~rm
    bm = nz & ~rm & ~gm
    h[rm] = (60.0 * ((g[rm] - b[rm]) / d[rm])) % 360.0
    h[gm] = 60.0 * ((b[gm] - r[gm]) / d[gm]) + 120.0
    h[bm] = 60.0 * ((r[bm] - g[bm]) / d[bm]) + 240.0
    s = np.where(mx > 1e-9, d / np.maximum(mx, 1e-9), 0.0)
    return h, s, mx


# fixed 2026-09-26T02:35:47Z (gate spec) -- hue ranges in degrees, (lo, hi) with lo > hi meaning wrap-around
COLOUR_RULES = {
    "o11": dict(hue=(292.0, 340.0), s_min=0.45, v_min=0.20),  # magenta marker (0.85, 0.00, 0.65)
    "o3": dict(hue=(345.0, 15.0), s_min=0.50, v_min=0.15),    # red mug (0.80, 0.08, 0.08)
    "o5": dict(hue=(205.0, 250.0), s_min=0.45, v_min=0.20),   # blue tray (0.10, 0.25, 0.85)
    "o8": dict(hue=(100.0, 160.0), s_min=0.45, v_min=0.15),   # green bottle (0.10, 0.65, 0.20)
}


# change 1 (2026-09-26T02:44Z, after the first G-cam run -- see the readiness doc): the lit top faces of the mug and
# the bottle render desaturated (pale pink / pale green, visible in gcam_sheet.jpg), so the v1 rule missed them and
# biased the centroid downwards. Only o3 / o8 change; o11 / o5 keep the v1 rule.
COLOUR_RULES_V2 = dict(COLOUR_RULES,
                       o3=dict(hue=(340.0, 25.0), s_min=0.20, v_min=0.15),
                       o8=dict(hue=(95.0, 170.0), s_min=0.15, v_min=0.15))


def colour_mask(img, obj: str, rules: dict | None = None) -> np.ndarray:
    h, s, v = rgb_to_hsv(img)
    r = (rules or COLOUR_RULES)[obj]
    lo, hi = r["hue"]
    hm = (h >= lo) & (h <= hi) if lo <= hi else (h >= lo) | (h <= hi)
    return hm & (s >= r["s_min"]) & (v >= r["v_min"])


# ------------------------------------------------------------------------------------------ FK with rotation
def _axis_rot(axis, q) -> np.ndarray:
    k = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    s, c = np.sin(q)[:, None, None], np.cos(q)[:, None, None]
    return np.eye(3) + s * K + (1 - c) * (K @ K)


def fk_pose(chain: list, q) -> tuple:
    """Same chain walk as harvest.train.se2e_data.fk_ee, also returning the rotation: q (N, 7) -> p (N, 3),
    R (N, 3, 3) of end_effector_{r|l}_link in the chain base (arm_base_link)."""
    q = np.asarray(q, float).reshape(-1, 7)
    n = len(q)
    R = np.broadcast_to(np.eye(3), (n, 3, 3)).copy()
    p = np.zeros((n, 3))
    i = 0
    for typ, xyz, Ro, axis in chain:
        p = p + R @ xyz
        R = R @ Ro
        if typ in ("revolute", "continuous"):
            R = R @ _axis_rot(axis, q[:, i])
            i += 1
    return p, R


def fit_offset(p_fk, R_fk, target) -> tuple:
    """Least squares target ~= p_fk + R_fk @ o + t (o in the end-effector frame, t constant): returns (o, t)."""
    n = len(p_fk)
    A = np.zeros((3 * n, 6))
    A[:, :3] = np.asarray(R_fk).reshape(3 * n, 3)
    A[:, 3:] = np.tile(np.eye(3), (n, 1))
    b = (np.asarray(target, float) - np.asarray(p_fk, float)).reshape(-1)
    x, *_ = np.linalg.lstsq(A, b, rcond=None)
    return x[:3], x[3:]


def apply_offset(p_fk, R_fk, o, t) -> np.ndarray:
    return np.asarray(p_fk) + np.einsum("nij,j->ni", np.asarray(R_fk), o) + t


def kabsch(A, B) -> tuple:
    """Rotation R and translation t minimising |R a + t - b| over rows."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca


def fit_rigid_offset(p_fk, R_fk, target, iters: int = 50) -> tuple:
    """target ~= Rb (p_fk + R_fk o) + t: alternate Kabsch (Rb, t) and linear o. Returns (Rb, t, o)."""
    p_fk, R_fk, target = np.asarray(p_fk, float), np.asarray(R_fk, float), np.asarray(target, float)
    o = np.zeros(3)
    Rb, t = np.eye(3), np.zeros(3)
    for _ in range(iters):
        Rb, t = kabsch(p_fk + np.einsum("nij,j->ni", R_fk, o), target)
        local = (target - t) @ Rb  # = Rb^T (target - t)
        A = R_fk.reshape(-1, 3)
        o, *_ = np.linalg.lstsq(A, (local - p_fk).reshape(-1), rcond=None)
    return Rb, t, o


def apply_rigid_offset(p_fk, R_fk, Rb, t, o) -> np.ndarray:
    return (np.asarray(p_fk) + np.einsum("nij,j->ni", np.asarray(R_fk), o)) @ Rb.T + t


# ------------------------------------------------------------------------------------------ statistics
def boot_ci(hits, n_boot: int = 10000, seed: int = 0) -> tuple:
    """Mean and 95 % percentile bootstrap interval of a 0/1 (or real) per-snapshot array."""
    x = np.asarray(hits, float)
    if len(x) == 0:
        return (math.nan, math.nan, math.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    m = x[idx].mean(1)
    return float(x.mean()), float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


DIRS8 = ("plus_x", "plus_x_plus_y", "plus_y", "minus_x_plus_y", "minus_x", "minus_x_minus_y", "minus_y",
         "plus_x_minus_y")


def dir8(dx: float, dy: float) -> str:
    """8-sector name of an xy direction (sector centres at multiples of 45 deg, +x = 0)."""
    a = math.degrees(math.atan2(dy, dx)) % 360.0
    return DIRS8[int(((a + 22.5) % 360.0) // 45.0)]
