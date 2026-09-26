"""Geometry for converting public robot data into our perception / control samples (pure numpy).

Conventions are explicit in every function name, because the sources disagree:
  MolmoBot (MuJoCo) and RoboTwin (SAPIEN) quaternions are w, x, y, z; BEHAVIOR (OmniGibson / Isaac) is x, y, z, w.
  'extrinsic_cv' in MolmoBot and RoboTwin = world -> camera, OpenCV axes (x right, y down, z forward).
  'cam2world_gl' = camera -> world with OpenGL axes (x right, y up, looking along -z); RoboTwin's extrinsic_cv equals
  inv(cam2world_gl @ diag(1, -1, -1, 1)); MolmoBot's cam2world_gl is simply inv(extrinsic_cv) (no flip, despite the
  name -- measured, docs/research/public_data_conversion_howto_2026-09-26.md 4.1).
  BEHAVIOR cam_rel_poses = camera -> robot base, OpenGL camera axes (their depth_to_pcd applies a 180 deg x rotation).
"""
from __future__ import annotations

import numpy as np

FLIP_GL_CV = np.diag([1.0, -1.0, -1.0, 1.0])


def quat_wxyz_to_mat(q) -> np.ndarray:
    w, x, y, z = np.asarray(q, float) / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def quat_xyzw_to_mat(q) -> np.ndarray:
    x, y, z, w = np.asarray(q, float)
    return quat_wxyz_to_mat([w, x, y, z])


def yaw_mat(yaw: float) -> np.ndarray:
    c, s = np.cos(yaw), np.sin(yaw)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def pose_to_T(p, R) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = np.asarray(R, float)
    T[:3, 3] = np.asarray(p, float)
    return T


def inv_T(T) -> np.ndarray:
    T = np.asarray(T, float)
    out = np.eye(4)
    out[:3, :3] = T[:3, :3].T
    out[:3, 3] = -T[:3, :3].T @ T[:3, 3]
    return out


def apply_T(T, p) -> np.ndarray:
    T = np.asarray(T, float)
    p = np.asarray(p, float)
    return p @ T[:3, :3].T + T[:3, 3]


def as_4x4(E) -> np.ndarray:
    E = np.asarray(E, float)
    if E.shape == (4, 4):
        return E
    out = np.eye(4)
    out[:3] = E
    return out


def world2cam_cv_from_cam2world_gl(C_gl) -> np.ndarray:
    return inv_T(np.asarray(C_gl, float) @ FLIP_GL_CV)


def project(K, E_world2cam, p):
    """-> (uv pixel (2,), depth z along the optical axis). z <= 0 means behind the camera."""
    pc = apply_T(as_4x4(E_world2cam), p)
    z = float(pc[2])
    if abs(z) < 1e-9:
        return np.array([np.nan, np.nan]), z
    uv = (np.asarray(K, float) @ pc)[:2] / z
    return uv, z


def rescale_K_vertical_fov(K, W: int, H: int) -> np.ndarray:
    """K stored for a square render (2cx x 2cy) whose fov is the VERTICAL fov of a W x H video with square pixels
    (MolmoBot head / wrist: 480 x 480 intrinsics, 1024 x 576 video)."""
    K = np.asarray(K, float)
    fy = K[1, 1] * H / (2 * K[1, 2])
    return np.array([[fy, 0.0, W / 2], [0.0, fy, H / 2], [0.0, 0.0, 1.0]])


def backproject(K, depth, mask, dmin: float = 0.05, dmax: float = 9.5) -> np.ndarray:
    """Camera-frame (CV) points of the masked pixels with valid depth (depth = distance to the image plane)."""
    K = np.asarray(K, float)
    v, u = np.nonzero(mask & (depth > dmin) & (depth < dmax))
    z = depth[v, u].astype(float)
    x = (u - K[0, 2]) * z / K[0, 0]
    y = (v - K[1, 2]) * z / K[1, 1]
    return np.c_[x, y, z]


def fit_plane(pts, iters: int = 200, tol: float = 0.01, rng=None):
    """RANSAC plane: -> (unit normal n with n.z >= 0, offset d with n.p = d, inlier fraction)."""
    pts = np.asarray(pts, float)
    rng = rng if rng is not None else np.random.default_rng(0)
    if len(pts) < 3:
        return np.array([0.0, 0.0, 1.0]), 0.0, 0.0
    best, best_n = None, 0
    for _ in range(iters):
        a, b, c = pts[rng.choice(len(pts), 3, replace=False)]
        n = np.cross(b - a, c - a)
        if np.linalg.norm(n) < 1e-9:
            continue
        n = n / np.linalg.norm(n)
        inl = np.abs((pts - a) @ n) < tol
        if inl.sum() > best_n:
            best, best_n = inl, int(inl.sum())
    if best is None:
        return np.array([0.0, 0.0, 1.0]), 0.0, 0.0
    q = pts[best]
    c = q.mean(0)
    n = np.linalg.svd(q - c)[2][-1]
    if n[2] < 0:
        n = -n
    return n, float(n @ c), best_n / len(pts)


def tilt_deg(axis_world) -> float:
    """Angle between a world direction and straight down (0 = pointing down)."""
    a = np.asarray(axis_world, float)
    return float(np.degrees(np.arccos(np.clip(-a[2] / np.linalg.norm(a), -1, 1))))


def approach_axis(Rs, vecs):
    """Which local axis (index, sign) of the EE frame points from the EE to the grasped object at grasp time.
    Rs: EE rotations (local -> world); vecs: object minus EE in world. -> (axis, sign, mean cosine)."""
    best = (0, 1, -2.0)
    for ax in range(3):
        for sg in (1, -1):
            cs = []
            for R, v in zip(Rs, vecs):
                v = np.asarray(v, float)
                if np.linalg.norm(v) < 1e-9:
                    continue
                cs.append(float(sg * np.asarray(R)[:, ax] @ v / np.linalg.norm(v)))
            s = float(np.mean(cs)) if cs else -2.0
            if s > best[2]:
                best = (ax, sg, s)
    return best
