"""Camera geometry for the probe (pure numpy).

Frames: robot base frame = the sim world frame (fixed robot root at the origin, scene.py): x forward, y left, z up, m.
Camera frame = OpenCV / ROS optical convention (x right, y down, z forward), which is Isaac Lab's `quat_w_ros`; its
depth output `distance_to_image_plane` is the optical z. `Cam.R` holds the camera axes as columns in the base frame
(R_base_from_cam), `Cam.t` the camera origin in the base frame.
Pixels: continuous image coordinates span [0, W] x [0, H]; the integer pixel index i has its centre at i + PIX_C.
Functions taking (u, v) take pixel INDICES (what a model reads off an image, may be fractional) unless stated.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

PIX_C = 0.5


@dataclass(frozen=True)
class Cam:
    name: str
    W: int
    H: int
    fx: float
    fy: float
    cx: float
    cy: float
    R: np.ndarray
    t: np.ndarray

    def to_json(self) -> dict:
        return {"name": self.name, "W": int(self.W), "H": int(self.H), "fx": float(self.fx), "fy": float(self.fy),
                "cx": float(self.cx), "cy": float(self.cy), "R": np.asarray(self.R, float).tolist(),
                "t": np.asarray(self.t, float).tolist()}

    @classmethod
    def from_json(cls, d: dict) -> "Cam":
        return cls(name=d["name"], W=int(d["W"]), H=int(d["H"]), fx=float(d["fx"]), fy=float(d["fy"]),
                   cx=float(d["cx"]), cy=float(d["cy"]), R=np.asarray(d["R"], float), t=np.asarray(d["t"], float))


def quat_to_R(q_wxyz) -> np.ndarray:
    w, x, y, z = (float(v) for v in q_wxyz)
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def quat_mul(a, b) -> np.ndarray:
    w1, x1, y1, z1 = (float(v) for v in a)
    w2, x2, y2, z2 = (float(v) for v in b)
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def quat_from_rotvec(rv) -> np.ndarray:
    rv = np.asarray(rv, float)
    th = float(np.linalg.norm(rv))
    if th < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    a = rv / th
    return np.array([math.cos(th / 2), *(a * math.sin(th / 2))])


def yaw_between(q, q0) -> float:
    """Rotation about base z (rad) of q relative to q0 (q = r * q0)."""
    w, x, y, z = quat_mul(q, np.array([q0[0], -q0[1], -q0[2], -q0[3]]))
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def project(cam: Cam, p) -> tuple:
    """Base-frame point -> (u, v) continuous image coordinates and optical depth z (z <= 0: behind the camera)."""
    pc = cam.R.T @ (np.asarray(p, float) - cam.t)
    z = float(pc[2])
    if z <= 1e-12:
        return float("nan"), float("nan"), z
    return float(cam.fx * pc[0] / z + cam.cx), float(cam.fy * pc[1] / z + cam.cy), z


def pixel_of(cam: Cam, p) -> tuple:
    """(iu, iv, inside): the pixel index containing the projection of p, and whether it is inside the image."""
    u, v, z = project(cam, p)
    if z <= 0 or not math.isfinite(u):
        return -1, -1, False
    iu, iv = int(math.floor(u)), int(math.floor(v))
    return iu, iv, bool(0 <= iu < cam.W and 0 <= iv < cam.H)


def pixel_ray(cam: Cam, u, v) -> tuple:
    """(origin, unit direction) in the base frame of the ray through pixel index (u, v)."""
    d = np.array([(float(u) + PIX_C - cam.cx) / cam.fx, (float(v) + PIX_C - cam.cy) / cam.fy, 1.0])
    d = cam.R @ d
    return np.asarray(cam.t, float).copy(), d / np.linalg.norm(d)


def lift_plane(cam: Cam, u, v, plane_z: float):
    """Intersection of the pixel ray with the horizontal plane z = plane_z (base frame), or None when the ray is
    parallel to it or meets it behind the camera."""
    o, d = pixel_ray(cam, u, v)
    if abs(d[2]) < 1e-9:
        return None
    s = (float(plane_z) - o[2]) / d[2]
    if s <= 0:
        return None
    return o + s * d


def triangulate(cam1: Cam, uv1, cam2: Cam, uv2) -> tuple:
    """Midpoint of the closest approach of two pixel rays and the gap between the rays (m). Parallel rays -> gap inf."""
    o1, d1 = pixel_ray(cam1, *uv1)
    o2, d2 = pixel_ray(cam2, *uv2)
    w0 = o1 - o2
    a, b, c = d1 @ d1, d1 @ d2, d2 @ d2
    d, e = d1 @ w0, d2 @ w0
    den = a * c - b * b
    if abs(den) < 1e-12:
        return (o1 + o2) / 2, float("inf")
    s = (b * e - c * d) / den
    t = (a * e - b * d) / den
    p1, p2 = o1 + s * d1, o2 + t * d2
    return (p1 + p2) / 2, float(np.linalg.norm(p1 - p2))


def lift_depth(cam: Cam, u, v, depth: np.ndarray, win: int = 2):
    """Pixel index + the camera's z-depth map -> base-frame point. An invalid depth (0, inf, nan) at the pixel falls
    back to the median of the valid depths in a (2 win + 1)^2 window; None when there is none."""
    iu, iv = int(round(float(u))), int(round(float(v)))
    if not (0 <= iu < cam.W and 0 <= iv < cam.H):
        return None
    z = float(depth[iv, iu])
    if not (math.isfinite(z) and z > 0):
        w = depth[max(0, iv - win):iv + win + 1, max(0, iu - win):iu + win + 1]
        w = w[np.isfinite(w) & (w > 0)]
        if w.size == 0:
            return None
        z = float(np.median(w))
    pc = np.array([(iu + PIX_C - cam.cx) / cam.fx * z, (iv + PIX_C - cam.cy) / cam.fy * z, z])
    return cam.R @ pc + cam.t


def plane_depth_map(cam: Cam, plane_z: float) -> np.ndarray:
    """Synthetic z-depth map of the plane z = plane_z (inf where the ray misses it); tests and fakes."""
    iu, iv = np.meshgrid(np.arange(cam.W) + PIX_C, np.arange(cam.H) + PIX_C)
    dc = np.stack([(iu - cam.cx) / cam.fx, (iv - cam.cy) / cam.fy, np.ones_like(iu)], axis=-1)  # z = 1
    dw = dc @ cam.R.T
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (plane_z - cam.t[2]) / dw[..., 2]
    s[~np.isfinite(s) | (s <= 0)] = np.inf
    return s  # optical z of the hit = s because dc has z = 1


def rotate_cam(cam: Cam, axis, deg: float) -> Cam:
    """The camera with its orientation rotated by deg about a base-frame axis through its origin (calibration error)."""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    th = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    Rot = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
    return Cam(cam.name, cam.W, cam.H, cam.fx, cam.fy, cam.cx, cam.cy, Rot @ cam.R, np.asarray(cam.t, float))


def sensitivity(head: Cam, wrist: Cam, p, rot_deg=0.5, pix=2.0, plane_dz=0.005, n=200, seed=0) -> dict:
    """Median 3D error (mm) of plane lift (head) and triangulation (head + wrist) for a true point p under:
    random extrinsic rotation errors of rot_deg (both cameras), uniform pixel noise +-pix, and a support-plane
    height error of plane_dz. p's plane lift uses the plane z = p[2]."""
    rng = np.random.default_rng(seed)
    p = np.asarray(p, float)
    uh, vh, _ = project(head, p)
    uw, vw, _ = project(wrist, p)
    uv_h, uv_w = (uh - PIX_C, vh - PIX_C), (uw - PIX_C, vw - PIX_C)

    def rnd_axis():
        a = rng.normal(size=3)
        return a / np.linalg.norm(a)

    out = {"plane_rot_mm": [], "plane_pix_mm": [], "tri_rot_mm": [], "tri_pix_mm": []}
    for _ in range(n):
        h2 = rotate_cam(head, rnd_axis(), rot_deg)
        w2 = rotate_cam(wrist, rnd_axis(), rot_deg)
        q = lift_plane(h2, *uv_h, p[2])
        out["plane_rot_mm"].append(np.linalg.norm(q - p) * 1e3 if q is not None else np.inf)
        out["tri_rot_mm"].append(np.linalg.norm(triangulate(h2, uv_h, w2, uv_w)[0] - p) * 1e3)
        dh, dw = rng.uniform(-pix, pix, 2), rng.uniform(-pix, pix, 2)
        q = lift_plane(head, uv_h[0] + dh[0], uv_h[1] + dh[1], p[2])
        out["plane_pix_mm"].append(np.linalg.norm(q - p) * 1e3 if q is not None else np.inf)
        out["tri_pix_mm"].append(np.linalg.norm(
            triangulate(head, (uv_h[0] + dh[0], uv_h[1] + dh[1]), wrist, (uv_w[0] + dw[0], uv_w[1] + dw[1]))[0] - p)
            * 1e3)
    r = {k: round(float(np.median(v)), 2) for k, v in out.items()}
    q = lift_plane(head, *uv_h, p[2] + plane_dz)
    r["plane_h_mm"] = round(float(np.linalg.norm(q - p) * 1e3), 2) if q is not None else float("inf")
    return r
