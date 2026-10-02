"""autotune geometry (pure numpy): grasp orientations, hand yaw period, camera visibility, body descriptors.

Conventions (shared with harvest/l9: curobo9 tool frame, hcam9 camera frame, r1b probe2/probe3):
- grasp/tool frame: z = -approach (from the fingers back to the wrist), y = finger closing axis. A top-down grasp at
  yaw 0 closes along world +x; yaw turns the closing axis about world z; tilt leans the approach by `tilt` towards
  the world heading `tdir` (0 = +x, away from the robot).
- camera: R columns = camera +X forward (optical axis), +Y left, +Z up; pitch = optical axis angle below horizontal.
- lean: forward pitch of the cuRobo config base link relative to its pose with every body joint at 0.
"""
from __future__ import annotations

import math

import numpy as np


def rot_y(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def rot_z(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def grasp_R(tilt: float, yaw: float, tdir: float) -> np.ndarray:
    """World rotation of the tool frame (columns x, y, z) -- same construction as r1b probe2.R_of."""
    a = np.array([math.sin(tilt) * math.cos(tdir), math.sin(tilt) * math.sin(tdir), -math.cos(tilt)])
    z = -a
    y0 = np.array([math.cos(yaw), math.sin(yaw), 0.0])
    y = y0 - z * float(y0 @ z)
    y /= np.linalg.norm(y)
    return np.column_stack([np.cross(y, z), y, z])


def yaw_period_deg(hand: dict) -> int:
    """180 when the hand is symmetric under a half turn about the approach (every opposition pair has the same
    number of tips on both sides, e.g. a parallel gripper), else 360 (thumb vs fingers)."""
    sym = all(len(a) == len(b) for a, b in hand["opposition"])
    return 180 if sym else 360


def orientations(hand: dict, yaw_step: int = 30, tilts=((0, 0), (30, 0), (30, 90))) -> list:
    """[{yaw_deg, tilt_deg, tdir_deg}] -- yaws over the hand's period, tilts as (tilt deg, heading deg). For the left
    arm the caller mirrors y, so tdir 90 means 'towards the robot's midline' for both arms."""
    out = []
    for t, td in tilts:
        for y in range(0, yaw_period_deg(hand), yaw_step):
            out.append({"yaw_deg": y, "tilt_deg": t, "tdir_deg": td})
    return out


def look_R(pitch_deg: float, pan_deg: float = 0.0) -> np.ndarray:
    """Camera rotation (cols fwd, left, up) looking pitch_deg below horizontal, heading pan_deg."""
    return rot_z(math.radians(pan_deg)) @ rot_y(math.radians(pitch_deg))


def cam_pitch_deg(R: np.ndarray) -> float:
    f = R[:, 0]
    return math.degrees(math.atan2(-f[2], f[0]))  # signed vs the robot heading +x: > 90 = looking backwards


def visible(cam: dict, P: np.ndarray, margin: float = 0.05, near: float = 0.05) -> np.ndarray:
    """Pinhole in-image test of world points P (N, 3). cam = {R (cols fwd,left,up), t, hfov (deg), width, height}."""
    pc = (np.asarray(P, float) - cam["t"]) @ cam["R"]  # columns: forward, left, up
    f = (cam["width"] / 2.0) / math.tan(math.radians(cam["hfov"]) / 2.0)
    depth = pc[:, 0]
    ok = depth > near
    d = np.where(ok, depth, 1.0)
    u = -pc[:, 1] / d * f
    v = -pc[:, 2] / d * f
    return ok & (np.abs(u) <= cam["width"] / 2.0 * (1 - margin)) & (np.abs(v) <= cam["height"] / 2.0 * (1 - margin))


def lean_rad(T: np.ndarray, T0: np.ndarray) -> float:
    """Forward pitch of a base frame T relative to its body-joints-at-zero pose T0 (both in the root frame)."""
    Rr = T0[:3, :3].T @ T[:3, :3]
    x = Rr[:, 0]
    return math.atan2(-x[2], x[0])


def body_grid(joints: dict, n: int) -> list:
    """Every combination of n evenly spaced values per body joint ({name: [lo, hi]}); [] joints -> [{}]."""
    names = sorted(joints)
    if not names:
        return [{}]
    axes = [np.linspace(joints[k][0], joints[k][1], n) for k in names]
    mesh = np.meshgrid(*axes, indexing="ij")
    flat = np.stack([m.ravel() for m in mesh], -1)
    return [{k: round(float(v), 5) for k, v in zip(names, row)} for row in flat]


def rot_euler(R: np.ndarray) -> tuple:
    """(roll, pitch, yaw) with R = Rz(yaw) Ry(pitch) Rx(roll) -- used only to group base rotations."""
    p = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    return math.atan2(R[2, 1], R[2, 2]), p, math.atan2(R[1, 0], R[0, 0])
