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
HFOV_RANGE = (65.0, 95.0)  # deg (outer bound, still used by the hold-out draw below; user 10-03 03시: the TRAINING
# draw itself is no longer uniform over this whole band -- see HFOV_CHOICES)
# hold-out bands (prereg §4 (ii-a)): one axis outside the training band -- unchanged (user 10-03: "hold 대역은 건드리지
# 말고 보고만", eval-only)
H_HOLD = ((0.25, 0.35), (0.80, 0.90))
PITCH_HOLD = ((22.0, 30.0), (62.0, 68.0))
HFOV_HOLD = ((55.0, 65.0), (95.0, 105.0))
# New episodes only (user 10-03 03시, spec amendment, L9_PRINCIPLES.md): HFOV is drawn from the robot's own real
# camera HFOV +/-5 deg in 5 deg steps, not uniformly over the old wide HFOV_RANGE band (a value far from the real
# lens was an unrealistic train-time axis). AIW ZED Mini STD_HFOV ~85 -> {80, 85, 90}; Franka D435 69 -> {64, 69,
# 74}. (R1 Pro ZED ~100.8 / G1 D435 69 +/-5: robot9.py V2 camera profiles, a different owner's file -- flagged,
# not changed here.)
HFOV_CHOICES = tuple(round(STD_HFOV + d, 2) for d in (-5.0, 0.0, 5.0))  # AIW: (80.0, 85.0, 90.0)

# Franka head camera mast (spec §9.2-r1, user 10-02 ~21:40 "머리 카메라가 로봇팔에 가려": the rev. smoke 2 mount
# (mast 0.23 m to the arm's left, pitch 38-55, h 0.45-0.70) sat on the SAME side the single right arm sweeps to
# reach the table (robot9.BASE_Y_RIGHT; the task's TCP box x 0.25..0.65, y -0.50..0.10 straddles the base's own
# y=0 line) and looked across at a shallow, near-horizontal angle -- the forearm was frequently between the mast
# and the TCP. docs/stage3/results/l9v2_gates.md "Franka camera r1": measured on 600 real pilotF/prodF* calls
# (head_depth.npz distance_to_image_plane vs. the TCP the ring marks, tools/l9/hcam9_occ_probe.py) 29.4 % of
# on-screen calls had > 50 % of the TCP's footprint occluded by the robot's own links (36.6 % the TCP pixel
# itself; 18.8 % of all calls had the TCP off-screen). r1-v1 (x forward 0.05..0.25, same y/h/pitch as below) moved
# the camera itself into the arm's own forward reach corridor (x > 0 = toward the table, the same direction the
# forearm extends) -- a same-seed A/B (14 Franka eps, the production occ>=0.5 field, harvest/teach_l8d/collect.py
# _occ/clutter_x.occlusion -- the target-object/place-target occlusion, not just the TCP) measured WORSE than the
# old mount (26.1 % vs 9.1 % of calls >50 % occluded, docs/stage3/results/l9v2_gates.md "Franka camera r1"):
# occ was 1.0 on many calls across every phase (approach/carry/retreat alike), i.e. a near-field object blocking
# almost the whole frame -- the forward-shifted high mast was hanging almost directly over the arm's own reach
# path. r1-v2 (x behind/at the base, same side as the old mount, negative y / higher / steeper pitch otherwise)
# measured WORSE again on the same 24 seeds (46.5 % vs the matched OLD 9.6 %; a head image confirmed it, a single
# white link fills the whole frame). Both r1-v1 and r1-v2 kept the mast within about the SAME lateral/height
# distance from panda_link0 as the old mount (|y| 0.15-0.33 m, h 0.45-0.80 m -- a few tens of cm); a 7-DOF arm
# swings its upper-arm link through a wide volume around the base in many configurations (not only straight
# toward the table), so any mast that close is liable to have a link sweep right past the lens regardless of
# which side it is on -- consistent with the OLD mount's own 26.1 % production rate. r1-v3: move the mast well
# OUTSIDE the arm's ~0.855 m reach sphere from its shoulder (euclidean distance from panda_link0 at the range's
# midpoint ~1.3 m, versus ~0.25-0.85 m for the old / r1-v1 / r1-v2 ranges) -- high and to the side opposite the
# old mount, pitched steeply down (near top-down, smaller apparent arm silhouette at this range) and panned back
# toward the workspace. A same-seed quick check (8 Franka eps) still measured 23.2 % >50 % occluded -- better than
# r1-v1/r1-v2 but still above target; owner hypothesis (10-02 ~22:30): near-vertical pitch (60-75 deg) looks down
# almost the SAME axis the gripper descends on a top-down grasp, so the hand itself (not a stray link) sits
# between the lens and the object during the final approach -- distinct from the self-occlusion r1-v1/v2 showed.
# r1-v4 (x/y/h unchanged from r1-v3, pitch lowered to 30-50) tested the opposite of the hypothesis: it measured
# WORSE than r1-v3 (47.5 % vs 20.0 %, approach-only 38.1 % vs 24.0 %, same 8 seeds) -- at this distance a shallow
# / oblique look crosses more of the cluttered scene volume on its way to the target (more chances for a wall,
# other furniture or the arm to sit on the ray), while a near-top-down look has a short, mostly-open path straight
# down. So steeper pitch helps at this range, not hurts; the earlier "hand on a top-down grasp" worry did not
# show up as the dominant effect here. r1-v5: keep r1-v3's x/y/h, push pitch even steeper (65-80, closer to
# vertical) to see if the trend continues below r1-v3's 20.0 %. Re-validating (same 8-seed quick check, then
# the full set) before switching production.
# r1-v6 (closer distance ~0.6-0.8 m, same steep pitch as r1-v3/v5): also run as its own deploy in parallel with
# r1-v5 -- results recorded in docs/stage3/results/l9v2_gates.md, not reflected in the constant below.
# r1-v7 (this commit, user 10-03 03시, the user directly reviewed a frame and still saw the arm covering the
# target -- the far-mount candidates (v3/v5/v6) also clipped the top of the scene, e.g. a tall shelf's upper
# part): back to the OLD production mount position (x/y/h/pan) -- not a far mast -- and ONLY back the pitch off
# the steepest OLD value toward horizontal, in discrete 5 deg steps: pitch = 55 (OLD's own steepest) minus a
# uniform-random choice of {0, 5, 10, 15} deg, i.e. {55, 50, 45, 40}, never shallower than OLD's old minimum (38).
# A rendered preview (tools/l9/pitch_preview.py, 3 production scenes x {+0,+5,+10,+15,+20} deg, same mast pose,
# no re-simulation between panels) is what the user is reviewing to pick the amount of "backing off" before this
# becomes the production range -- see docs/stage3/results/l9v2_gates.md for the chosen panel / final numbers.
PITCH_OLD_STEEPEST = 55.0
MAST_DEFAULT = {"x": -0.10, "y": 0.23, "h": 0.55, "pitch": PITCH_OLD_STEEPEST - 5.0, "pan": -10.0}
MAST_RANGE = {"x": (-0.20, 0.0), "y": (0.15, 0.30), "h": (0.45, 0.70),
              "pitch": [PITCH_OLD_STEEPEST - off for off in (0.0, 5.0, 10.0, 15.0)], "pan": (-20.0, 0.0)}
D435_HFOV = 69.0  # Intel RealSense D435 colour, horizontal (datasheet 69 x 42 deg)
FRANKA_HFOV_CHOICES = tuple(round(D435_HFOV + d, 2) for d in (-5.0, 0.0, 5.0))  # (64.0, 69.0, 74.0), user 10-03
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


def _choice(rng, choices) -> float:
    return float(rng.choice(np.asarray(choices, float)))


def draw_ffw(seed: int, h0: float, attempt: int = 0) -> dict:
    """Training band: dz with h0 + dz inside H_RANGE (h0 = standard camera height above the surface after the
    neck draw), a pitch target and a horizontal FOV (user 10-03: drawn from HFOV_CHOICES, the real lens +/-5 deg
    in 5 deg steps, not uniformly over HFOV_RANGE)."""
    rng = _rng(seed, attempt, 1)
    lo = max(-DZ_MAX, H_RANGE[0] - h0)
    hi = min(DZ_MAX, H_RANGE[1] - h0)
    dz = _u(rng, (lo, hi)) if hi > lo else float(np.clip(0.0, H_RANGE[0] - h0, H_RANGE[1] - h0))
    return {"mode": "rand", "dz": round(dz, 4), "pitch": round(_u(rng, PITCH_RANGE), 2),
            "hfov": round(_choice(rng, HFOV_CHOICES), 2), "attempt": int(attempt)}


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
    """Per MAST_RANGE axis: a list -> a discrete uniform choice (e.g. r1-v7's pitch), a (lo, hi) tuple -> a
    continuous uniform draw. hfov: a discrete choice from FRANKA_HFOV_CHOICES (user 10-03; was fixed D435_HFOV)."""
    if default:
        return dict(MAST_DEFAULT, mode="mast_default", hfov=D435_HFOV, attempt=int(attempt))
    rng = _rng(seed, attempt, 3)
    out = {k: round(_choice(rng, r) if isinstance(r, list) else _u(rng, r), 4) for k, r in MAST_RANGE.items()}
    return dict(out, mode="mast", hfov=round(_choice(rng, FRANKA_HFOV_CHOICES), 2), attempt=int(attempt))


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
