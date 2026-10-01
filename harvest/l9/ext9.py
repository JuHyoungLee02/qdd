"""L9 v2 external (world-fixed) cameras rendered in pairs with the head camera (user 10-02 03h: third person allowed
only as paired views; NOW §6, spec §12.6). Pure (no Isaac).

A paired episode (deterministic per-seed coin, P_DEFAULT of the episodes) renders 1-2 cameras fixed in the room --
tripod / wall / ceiling-like poses drawn per episode -- at the same moments as the head camera (every call): same
state, same 3D targets, so the build can project the head label into the external view. Nothing changes for an
episode whose coin is off (no prims written, no files, no meta keys).

Pose convention = hcam9 (Isaac "world" camera convention: columns = camera +X forward, +Y left, +Z up, in the env
frame = the frame of the head entry of cams.json); `optical(R)` is the base_from_optical matrix cams.json records.
A draw is valid when the workspace points (the task objects) and the robot points (head camera, TCP) all project
inside the image (MARGIN), no furniture box / robot torso lies on the line of sight, the camera stands inside the
room's clear zone (no wall between it and the robot) and outside furniture; the rendered depth check (`depth_ok`)
then rejects a pose with something right in front of the lens or a hidden point (redraw, then no external view)."""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field

import numpy as np

from . import hcam9 as HC

VERSION = "ext9-v1"
P_DEFAULT = 0.30  # share of paired episodes (user 10-02: start with 30 %)
W, H = 672, 376  # = the head render size (same image token cost)
HFOV = (55.0, 90.0)  # deg, rectilinear only (no fisheye): D435 69, Azure Kinect 75 / 90, ZED 2 colour ~ 90 (cropped)
KINDS = ("tripod", "wall", "ceiling")
KIND_P = (0.5, 0.3, 0.2)
H_RANGE = {"tripod": (1.00, 1.70), "wall": (1.70, 2.30), "ceiling": (2.10, 2.50)}  # camera height above the floor, m
DIST = {"tripod": (0.90, 1.60), "wall": (1.10, 1.80), "ceiling": (0.35, 1.00)}  # horizontal distance to the look point
LOOK_TOWARD_ROBOT = (0.15, 0.40)  # look point = workspace centre moved this share towards the robot points
LOOK_JITTER = 0.05
MARGIN = 0.06  # image border share every must-see point stays inside
MIN_Z = 0.30
MIN_AZ_GAP = 45.0  # deg between the two cameras of one episode
BOX_MARGIN = 0.12  # the lens stays this far outside furniture boxes
SUB_TRIES = 80
ROOM_ZONE = ((-0.45, 1.25), (-1.05, 0.85))  # = scene9.ZONE shrunk by 5 cm (the room's clear box: no walls inside)
ROBOT_KEEP_OUT = ((-0.40, 0.15), (-0.45, 0.45), (0.0, 2.0))  # = assets_x.furniture.KEEP_OUT (no lens inside)
ROBOT_TORSO = ((-0.35, 0.10), (-0.30, 0.30), (0.0, 1.55))  # occluder of workspace points (the robot body)
NEAR_M, NEAR_FRAC, OCC_TOL = 0.35, 0.05, 0.25
TRIES = 4  # rendered redraws per camera, then the episode keeps fewer (or no) external views
M_OPT = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])  # = world_isaac.WORLD_CONV_TO_OPTICAL


@dataclass
class Ctx:
    """What a draw must see: look_ws = workspace centre, ws_pts (task objects), robot_pts (head camera, TCP),
    boxes = furniture parts {pos, size, yaw} (env frame), zone = the room's clear xy box (None: no room)."""
    look_ws: np.ndarray
    robot_pts: list
    ws_pts: list
    boxes: list = field(default_factory=list)
    zone: tuple | None = ROOM_ZONE
    surface_z: float = 0.8


# ------------------------------------------------------------------ coin
def _u01(tag: str) -> float:
    return int(hashlib.sha256(tag.encode()).hexdigest()[:12], 16) / float(16 ** 12)


def coin(seed: int, p: float = P_DEFAULT) -> bool:
    """True for a share p of the seeds (fixed per seed; independent of hcam9.coin)."""
    return _u01(f"l9-ext:{int(seed)}") < float(p)


def n_cams(seed: int, n_max: int = 1) -> int:
    return 1 if n_max <= 1 else (2 if _u01(f"l9-ext-n:{int(seed)}") < 0.5 else 1)


# ------------------------------------------------------------------ geometry
def K_of(hfov: float) -> np.ndarray:
    return HC.K_of(hfov, W, H)


def look_at(t, p) -> np.ndarray:
    """World-convention rotation of a camera at t looking at p, no roll (camera left horizontal)."""
    f = np.asarray(p, float) - np.asarray(t, float)
    f = f / np.linalg.norm(f)
    left = np.cross([0.0, 0.0, 1.0], f)
    left = left / np.linalg.norm(left)
    return np.column_stack([f, left, np.cross(f, left)])


def optical(R) -> np.ndarray:
    return np.asarray(R, float) @ M_OPT


def project(R, t, K, p) -> tuple:
    pc = optical(R).T @ (np.asarray(p, float) - np.asarray(t, float))
    z = float(pc[2])
    if abs(z) < 1e-9:
        return float("nan"), float("nan"), z
    return float(K[0, 0] * pc[0] / z + K[0, 2]), float(K[1, 1] * pc[1] / z + K[1, 2]), z


def _local(p, box) -> tuple:
    c = np.asarray(box["pos"], float)
    yaw = float(box.get("yaw", 0.0))
    cy, sy = math.cos(-yaw), math.sin(-yaw)
    d = np.asarray(p, float) - c
    return np.array([cy * d[0] - sy * d[1], sy * d[0] + cy * d[1], d[2]]), np.asarray(box["size"], float) / 2


def inside_any(p, boxes, margin: float) -> bool:
    for b in boxes:
        q, h = _local(p, b)
        if np.all(np.abs(q) <= h + margin):
            return True
    return False


def ray_blocked(a, b, boxes) -> bool:
    """The segment a -> b crosses one of the boxes (boxes holding an end point are skipped)."""
    for box in boxes:
        qa, h = _local(a, box)
        qb, _ = _local(b, box)
        if np.all(np.abs(qa) <= h + 0.005) or np.all(np.abs(qb) <= h + 0.005):
            continue
        h = h - 0.001
        d = qb - qa
        t0, t1 = 0.0, 1.0
        hit = True
        for k in range(3):
            if abs(d[k]) < 1e-12:
                if abs(qa[k]) > h[k]:
                    hit = False
                    break
                continue
            s0, s1 = (-h[k] - qa[k]) / d[k], (h[k] - qa[k]) / d[k]
            t0, t1 = max(t0, min(s0, s1)), min(t1, max(s0, s1))
            if t0 > t1:
                hit = False
                break
        if hit:
            return True
    return False


def _box(lim) -> dict:
    (x0, x1), (y0, y1), (z0, z1) = lim
    return {"pos": [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], "size": [x1 - x0, y1 - y0, z1 - z0], "yaw": 0.0}


def robot_box() -> dict:
    return _box(ROBOT_KEEP_OUT)


def az_gap(a: float, b: float) -> float:
    d = abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)
    return d


# ------------------------------------------------------------------ draws
def pose_of(d: dict) -> tuple:
    t = np.asarray(d["pos"], float)
    return look_at(t, d["look"]), t, K_of(d["hfov"])


def sees(R, t, K, ctx: Ctx) -> bool:
    torso = _box(ROBOT_TORSO)
    for p in list(ctx.ws_pts) + list(ctx.robot_pts):
        u, v, z = project(R, t, K, p)
        if not (z > MIN_Z and MARGIN * W <= u <= (1 - MARGIN) * W and MARGIN * H <= v <= (1 - MARGIN) * H):
            return False
        if ray_blocked(t, p, ctx.boxes):
            return False
    return not any(ray_blocked(t, p, [torso]) for p in ctx.ws_pts)


def draw(seed: int, attempt: int, ctx: Ctx, cam: int = 0, avoid=()) -> dict | None:
    """One external camera pose (meta pose_draw), or None when no valid pose was found in SUB_TRIES samples."""
    rng = np.random.default_rng([int(seed), 9431, int(cam), int(attempt)])
    k0 = int(rng.choice(len(KINDS), p=KIND_P))  # the kind is drawn once (filtering must not skew the shares);
    order = [KINDS[k0]] + [k for k in KINDS if k != KINDS[k0]]  # other kinds only when it has no valid pose
    for kind in order:
        d = _draw_kind(rng, kind, attempt, ctx, cam, avoid)
        if d is not None:
            return d
    return None


def _draw_kind(rng, kind: str, attempt: int, ctx: Ctx, cam: int, avoid) -> dict | None:
    ws = np.asarray(ctx.look_ws, float)
    rc = np.mean(np.asarray(ctx.robot_pts, float), axis=0)
    for sub in range(SUB_TRIES):
        f = float(rng.uniform(*LOOK_TOWARD_ROBOT))
        look = ws + f * (rc - ws) + rng.uniform(-LOOK_JITTER, LOOK_JITTER, 3)
        az = float(rng.uniform(-180.0, 180.0))
        dist = float(rng.uniform(*DIST[kind]))
        hgt = float(rng.uniform(*H_RANGE[kind]))
        hfov = float(rng.uniform(*HFOV))
        if any(az_gap(az, a["az"]) < MIN_AZ_GAP for a in avoid):
            continue
        t = np.array([look[0] + dist * math.cos(math.radians(az)), look[1] + dist * math.sin(math.radians(az)), hgt])
        if ctx.zone is not None:
            (x0, x1), (y0, y1) = ctx.zone
            if not (x0 <= t[0] <= x1 and y0 <= t[1] <= y1):
                continue
        if inside_any(t, [robot_box()], 0.10) or inside_any(t, ctx.boxes, BOX_MARGIN):
            continue
        if t[2] - look[2] < 0.05:  # never looking up at the workspace
            continue
        R = look_at(t, look)
        K = K_of(hfov)
        if not sees(R, t, K, ctx):
            continue
        p, pan = HC.pitch_pan(R)
        return {"version": VERSION, "kind": kind, "cam": int(cam), "pos": [round(float(v), 4) for v in t],
                "look": [round(float(v), 4) for v in look], "az": round(az, 2), "dist": round(dist, 4),
                "height_floor_m": round(hgt, 4), "height_above_surface_m": round(hgt - float(ctx.surface_z), 4),
                "hfov": round(hfov, 2), "pitch_deg": round(p, 2), "pan_deg": round(pan, 2),
                "attempt": int(attempt), "sub": int(sub)}
    return None


# ------------------------------------------------------------------ rendered check
def depth_ok(depth, R, t, K, pts, near: float = NEAR_M, near_frac: float = NEAR_FRAC, tol: float = OCC_TOL) -> tuple:
    """(ok, reason) from the camera's rendered z-depth: little right in front of the lens (a wall / furniture) and
    every must-see point not hidden behind something more than tol nearer than it."""
    d = np.asarray(depth, float)
    fin = np.isfinite(d) & (d > 0)
    share = float((fin & (d < near)).mean())
    if share > near_frac:
        return False, f"near: {share:.3f} of the pixels closer than {near} m"
    for i, p in enumerate(pts):
        u, v, z = project(R, t, K, p)
        if not (z > 0 and 0 <= u < d.shape[1] and 0 <= v < d.shape[0]):
            return False, f"outside: point {i}"
        win = d[max(0, int(v) - 2):int(v) + 3, max(0, int(u) - 2):int(u) + 3]
        win = np.where(np.isfinite(win) & (win > 0), win, 1e9)
        if float(np.median(win)) < z - tol:
            return False, f"occluded: point {i} depth {float(np.median(win)):.2f} m < {z:.2f} m"
    return True, "ok"


# ------------------------------------------------------------------ records / text
def record(name: str, d: dict) -> dict:
    """cams.json / meta entry of a drawn camera (G.Cam fields + view, K, hfov, pose_draw)."""
    R, t, K = pose_of(d)
    return {"name": name, "view": "external", "W": W, "H": H, "fx": float(K[0, 0]), "fy": float(K[1, 1]),
            "cx": float(K[0, 2]), "cy": float(K[1, 2]), "K": K.tolist(), "R": optical(R).tolist(),
            "t": [float(v) for v in t], "hfov_deg": float(d["hfov"]), "pose_draw": d}


def line(rec: dict, source: str) -> str:
    """The `camera:` line of an external row (same fields as hcam9.line, view word 'external')."""
    return HC.line(rec, source + "/external").replace("camera: head,", "camera: external,", 1)


def _cam_text(rec: dict) -> str:
    from ..astra_motion.prompts import CAM
    return CAM.format(W=rec["W"], H=rec["H"], t=list(rec["t"]), R=np.asarray(rec["R"], float).tolist())


_IMG1 = re.compile(r"^- Image 1: head camera, fixed on [^\n]*?, \d+x\d+ px at [^\n]*$", re.M)
_SWAPS = (("(the head camera)", "(the external camera)"), ("the head camera's depth", "the external camera's depth"),
          ("HEAD IMAGE OVERLAY", "IMAGE 1 OVERLAY"), ("The head view alone", "The external view alone"))
_NOTE = re.compile(r"\nNOTE: [^\n]*head image[^\n]*")
NOTE_TCP = "\nNOTE: the TCP is outside image 1 this time: no ring is drawn."


def external_text(text: str, rec: dict, tcp_drawn: bool) -> str:
    """A head-row request turned into the request of the same state seen by the external camera rec."""
    if len(_IMG1.findall(text)) != 1:
        raise ValueError("no single head-camera 'Image 1' line")
    out = _IMG1.sub(lambda m: "- Image 1: external camera, fixed in the room (not on the robot), " + _cam_text(rec),
                    text)
    for a, b in _SWAPS:
        out = out.replace(a, b)
    out = _NOTE.sub("", out)
    return out if tcp_drawn else out + NOTE_TCP


def external_answer(answer: str, point, rot: int | None = None) -> str:
    """The head row's answer with point_2d replaced by the external view's verified point and (format v2) `rot` by
    the grasp's closing-axis angle in the external image; every other field unchanged."""
    a = json.loads(answer)
    c = a.get("command") or {}
    if c.get("point_2d") is not None:  # (lift rows carry point_2d null: unchanged)
        if point is None:
            raise ValueError("a point command needs the external point")
        c["point_2d"] = [int(point[0]), int(point[1])]
    if c.get("rot") is not None:
        if rot is None:
            raise ValueError("a v2 grasp command needs the external rot")
        c["rot"] = int(rot)
    return json.dumps(a)


# ------------------------------------------------------------------ the same 3D target in the external view (build)
VIS_TOL = 0.02  # m: the external depth must reach the point (within this) for it to count as visible


def back_project(cam: dict, depth, point_2d) -> np.ndarray | None:
    """0-1000 point of a camera (cams.json entry) + its z-depth -> the env-frame 3D point it shows."""
    d = np.asarray(depth, float)
    u = float(point_2d[0]) / 1000.0 * cam["W"]
    v = float(point_2d[1]) / 1000.0 * cam["H"]
    i, j = min(max(int(v), 0), d.shape[0] - 1), min(max(int(u), 0), d.shape[1] - 1)
    z = float(d[i, j])
    if not (np.isfinite(z) and z > 0):
        return None
    pc = np.array([(u - cam["cx"]) / cam["fx"] * z, (v - cam["cy"]) / cam["fy"] * z, z])
    return np.asarray(cam["R"], float) @ pc + np.asarray(cam["t"], float)


def external_point(head: dict, head_depth, point_2d, ext: dict, ext_depth, tol: float = VIS_TOL) -> tuple:
    """The head label's 3D point (back-projected with the head depth) as a 0-1000 point of the external camera, when
    the external depth shows that point (not hidden). -> (point or None, info)."""
    P = back_project(head, head_depth, point_2d)
    if P is None:
        return None, {"why": "no_head_depth"}
    pc = np.asarray(ext["R"], float).T @ (P - np.asarray(ext["t"], float))
    z = float(pc[2])
    if z <= MIN_Z:
        return None, {"why": "behind"}
    u, v = ext["fx"] * pc[0] / z + ext["cx"], ext["fy"] * pc[1] / z + ext["cy"]
    if not (0 <= u < ext["W"] and 0 <= v < ext["H"]):
        return None, {"why": "outside"}
    d = np.asarray(ext_depth, float)
    win = d[max(0, int(v) - 1):int(v) + 2, max(0, int(u) - 1):int(u) + 2]
    win = win[np.isfinite(win)]
    if win.size == 0 or float(np.min(np.abs(win - z))) > tol:
        return None, {"why": "hidden", "z": round(z, 4), "d": None if win.size == 0 else round(float(np.median(win)), 4)}
    return [int(round(u / ext["W"] * 1000)), int(round(v / ext["H"] * 1000))], {"why": "ok", "P": [round(float(x), 4) for x in P]}


# ------------------------------------------------------------------ depth files (uint16 mm: 3x faster, 5x smaller)
def depth_to_mm(depth) -> np.ndarray:
    """z-depth (m) -> uint16 millimetres; 0 = no hit / beyond 65.5 m / invalid."""
    d = np.asarray(depth, np.float64)
    ok = np.isfinite(d) & (d > 0) & (d < 65.535)
    return np.where(ok, np.round(np.where(ok, d, 0.0) * 1000.0), 0).astype(np.uint16)


def load_depth(path: str) -> np.ndarray:
    """An external<k>_depth.npz (depth_mm) or a float depth npz (depth) -> float32 metres (inf = no hit)."""
    z = np.load(path)
    if "depth_mm" in z:
        mm = z["depth_mm"].astype(np.float32)
        return np.where(mm > 0, mm / 1000.0, np.inf).astype(np.float32)
    return np.asarray(z["depth"], np.float32)


def grasp_rot(rec: dict, c1, c2) -> dict:
    """Format v2 `rot` of a grasp (finger contacts c1, c2) as seen by camera rec (grasp9.rot_img, same convention
    as the head label): {"rot_deg_img", "rot_bin_img"}."""
    from . import grasp9 as G
    c1, c2 = np.asarray(c1, float), np.asarray(c2, float)
    c = (c2 - c1) / max(float(np.linalg.norm(c2 - c1)), 1e-9)
    deg, b = G.rot_img((c1 + c2) / 2, c, np.asarray(rec["K"], float), np.asarray(rec["R"], float),
                       np.asarray(rec["t"], float))
    return {"rot_deg_img": round(float(deg), 2), "rot_bin_img": int(b)}


WS_LIFT = 0.05  # m: workspace must-see points = object centres raised to about their tops (a compartment's object
# centre lies under its board: from above every camera 'sees' only the board, smoke s7)


def must_see(centres) -> list:
    return [np.asarray(p, float) + np.array([0.0, 0.0, WS_LIFT]) for p in centres]
