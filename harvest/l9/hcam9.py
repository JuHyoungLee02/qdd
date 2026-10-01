"""L9 head camera geometry (spec §9.3, docs/stage3/prereg_hcam8.md; pure, no Isaac).

A camera pose here is (R, t): R = rotation of the camera in Isaac's "world" camera convention (columns = camera +X
forward, +Y left, +Z up) expressed in the robot / world frame, t = optical centre. Pitch = angle of the optical axis
below the horizontal (deg, down positive), pan = its heading (deg, +y = left).

FFW-SG2 (E-HCAM8): half of the episodes (sha256 coin of the seed) keep the standard head camera (the robot's ZED Mini
on head_link2, the neck drawn by vary9); the other half move the mount vertically (dz), re-pitch the camera about
the horizontal axis (pan kept) and change the horizontal field of view (672 x 376 fixed). Hold-out draws put exactly
one axis outside the training band. Franka (mast on panda_link0): position / height / pitch / pan drawn per episode.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np

W, H = 672, 376  # head render size (every head camera of L9)
STD_HFOV = 2.0 * math.degrees(math.atan(336.0 / 367.0))  # 85.0 deg: ZED Mini WVGA fx 367 (FFW_SG2_REAL_cameras)

# E-HCAM8 training band (prereg §1)
H_RANGE = (0.35, 0.80)  # camera height above the work surface, m
DZ_MAX = 0.15  # vertical mount shift, m
PITCH_RANGE = (30.0, 62.0)  # deg
HFOV_RANGE = (65.0, 95.0)  # deg
# hold-out bands (prereg §4 (ii-a)): one axis outside the training band
H_HOLD = ((0.25, 0.35), (0.80, 0.90))
PITCH_HOLD = ((22.0, 30.0), (62.0, 68.0))
HFOV_HOLD = ((55.0, 65.0), (95.0, 105.0))

# Franka head camera mast (spec §9.2, rev. smoke 2): default and per-episode ranges, in the panda_link0 frame
# (x forward, y left). Like a humanoid head between the shoulders: the mast stands 0.23 m to the arm's left (the
# AI Worker head is at y 0, its right shoulder at y -0.23); behind the base the elbow filled the view (smoke 2).
MAST_DEFAULT = {"x": -0.10, "y": 0.23, "h": 0.55, "pitch": 45.0, "pan": -10.0}
MAST_RANGE = {"x": (-0.20, 0.0), "y": (0.15, 0.30), "h": (0.45, 0.70), "pitch": (38.0, 55.0), "pan": (-20.0, 0.0)}
D435_HFOV = 69.0  # Intel RealSense D435 colour, horizontal (datasheet 69 x 42 deg)
TRIES = 5


def fx_from_hfov(hfov_deg: float, width: int = W) -> float:
    return (width / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)


def hfov_from_fx(fx: float, width: int = W) -> float:
    return 2.0 * math.degrees(math.atan(width / 2.0 / fx))


def K_of(hfov_deg: float, width: int = W, height: int = H) -> np.ndarray:
    f = fx_from_hfov(hfov_deg, width)
    return np.array([[f, 0.0, width / 2.0], [0.0, f, height / 2.0], [0.0, 0.0, 1.0]])


# ------------------------------------------------------------------ rotations (quaternions w, x, y, z)
def quat_to_R(q) -> np.ndarray:
    w, x, y, z = (float(v) for v in q)
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def R_to_quat(R) -> tuple:
    R = np.asarray(R, float)
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = (0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s)
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = ((R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s)
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = ((R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s)
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = ((R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s)
    q = np.asarray(q, float)
    q = q / np.linalg.norm(q)
    return tuple(float(v) for v in (q if q[0] >= 0 else -q))


def axis_angle_R(axis, ang: float) -> np.ndarray:
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def look_R(pitch_deg: float, pan_deg: float) -> np.ndarray:
    """World-convention camera rotation with no roll: yaw = pan, then pitch down."""
    return axis_angle_R((0, 0, 1), math.radians(pan_deg)) @ axis_angle_R((0, 1, 0), math.radians(pitch_deg))


def pitch_pan(R) -> tuple:
    f = np.asarray(R, float)[:, 0]
    return math.degrees(math.asin(max(-1.0, min(1.0, -f[2])))), math.degrees(math.atan2(f[1], f[0]))


def repitch(R, pitch_deg: float) -> np.ndarray:
    """R turned about the horizontal axis normal to its optical axis so the axis dips pitch_deg (heading kept)."""
    R = np.asarray(R, float)
    p0, pan = pitch_pan(R)
    axis = (-math.sin(math.radians(pan)), math.cos(math.radians(pan)), 0.0)  # +pitch about it tips the axis down
    return axis_angle_R(axis, math.radians(pitch_deg - p0)) @ R


def mount_of(p_parent, q_parent, t_cam, R_cam) -> tuple:
    """(pos, quat) of the camera in its parent link from world poses (the mount transform format of
    FFW_SG2_REAL_cameras.mount_transform: position + world-convention quaternion in the link frame)."""
    Rp = quat_to_R(q_parent)
    pos = Rp.T @ (np.asarray(t_cam, float) - np.asarray(p_parent, float))
    return tuple(float(v) for v in pos), R_to_quat(Rp.T @ np.asarray(R_cam, float))


def realized(R, t, surface_z: float, floor_z: float = 0.0) -> dict:
    p, pan = pitch_pan(R)
    return {"height_above_surface_m": round(float(t[2]) - float(surface_z), 4),
            "height_floor_m": round(float(t[2]) - float(floor_z), 4), "pitch_deg": round(p, 2), "pan_deg": round(pan, 2)}


# ------------------------------------------------------------------ draws
def coin(seed: int) -> str:
    """'rand' for half of the seeds, 'std' for the other half (fixed per seed)."""
    return "rand" if int(hashlib.sha256(f"l9-hcam:{int(seed)}".encode()).hexdigest()[:8], 16) % 2 else "std"


def _rng(seed: int, attempt: int, tag: int):
    return np.random.default_rng([int(seed), 977, int(tag), int(attempt)])


def _u(rng, lo_hi) -> float:
    return float(rng.uniform(*lo_hi))


def draw_ffw(seed: int, h0: float, attempt: int = 0) -> dict:
    """Training band: dz with h0 + dz inside H_RANGE (h0 = standard camera height above the surface after the
    neck draw), a pitch target and a horizontal FOV."""
    rng = _rng(seed, attempt, 1)
    lo = max(-DZ_MAX, H_RANGE[0] - h0)
    hi = min(DZ_MAX, H_RANGE[1] - h0)
    dz = _u(rng, (lo, hi)) if hi > lo else float(np.clip(0.0, H_RANGE[0] - h0, H_RANGE[1] - h0))
    return {"mode": "rand", "dz": round(dz, 4), "pitch": round(_u(rng, PITCH_RANGE), 2),
            "hfov": round(_u(rng, HFOV_RANGE), 2), "attempt": int(attempt)}


def draw_hold_ffw(seed: int, h0: float, attempt: int = 0) -> dict:
    """Hold-out band: one axis (height / pitch / hfov, uniform) outside the training band, the others inside it.
    The height is set exactly (dz = target - h0, not limited to DZ_MAX)."""
    rng = _rng(seed, attempt, 2)
    axis = ("height", "pitch", "hfov")[int(rng.integers(3))]
    side = int(rng.integers(2))
    h = _u(rng, H_HOLD[side]) if axis == "height" else _u(rng, H_RANGE)
    p = _u(rng, PITCH_HOLD[side]) if axis == "pitch" else _u(rng, PITCH_RANGE)
    f = _u(rng, HFOV_HOLD[side]) if axis == "hfov" else _u(rng, HFOV_RANGE)
    return {"mode": "hold", "axis": axis, "dz": round(h - h0, 4), "pitch": round(p, 2), "hfov": round(f, 2),
            "attempt": int(attempt)}


def std_ffw() -> dict:
    return {"mode": "std", "dz": 0.0, "pitch": None, "hfov": round(STD_HFOV, 2), "attempt": 0}


def draw_mast(seed: int, attempt: int = 0, default: bool = False) -> dict:
    if default:
        return dict(MAST_DEFAULT, mode="mast_default", hfov=D435_HFOV, attempt=int(attempt))
    rng = _rng(seed, attempt, 3)
    out = {k: round(_u(rng, r), 4) for k, r in MAST_RANGE.items()}
    return dict(out, mode="mast", hfov=D435_HFOV, attempt=int(attempt))


def mast_pose(base_pos, surface_z: float, d: dict) -> tuple:
    """World (R, t) of the Franka mast camera: base_pos = panda_link0 origin (identity orientation)."""
    b = np.asarray(base_pos, float)
    t = np.array([b[0] + d["x"], b[1] + d["y"], float(surface_z) + d["h"]])
    return look_R(d["pitch"], d["pan"]), t


def ffw_pose(R0, t0, d: dict) -> tuple:
    """World (R, t) of a moved FFW head camera from its standard pose (R0, t0) after the neck draw."""
    t = np.asarray(t0, float) + np.array([0.0, 0.0, float(d.get("dz") or 0.0)])
    R = np.asarray(R0, float) if d.get("pitch") is None else repitch(R0, float(d["pitch"]))
    return R, t


def line(cam: dict, source: str) -> str:
    """The prereg §2 `camera:` text line (change 1) from a cams.json head entry (W, H, fx, fy, cx, cy, R, t; R =
    optical base_from_optical as recorded): intrinsics, height above the floor (robot-frame z = 0), pitch, pan -- what
    the robot knows at run time from camera_info and its joints; never the work-surface height (d-min hides it)."""
    from_opt = np.asarray(cam["R"], float) @ np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]]).T
    r = realized(from_opt, cam["t"], 0.0)
    return (f"camera: head, {int(cam['W'])}x{int(cam['H'])} px, fx {round(cam['fx'])} fy {round(cam['fy'])} "
            f"cx {round(cam['cx'])} cy {round(cam['cy'])}, {r['height_floor_m']:.2f} m above the floor, "
            f"pitch {round(r['pitch_deg'])} deg down, pan {round(r['pan_deg'])} deg; source: {source}")
