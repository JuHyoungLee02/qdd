"""L9 v2 grasp candidate physics test (spec §12.4 step 2, §12.12 gap classes): pure helpers for tools/l9/grasp_test.py.

Frames (as harvest/l9/grasp9.py): object canonical frame (bbox centre of the upright object, z up); G = TCP frame
(z_G = -approach, y_G = closing axis). The floating gripper URDF (assets9/grippers/<name>.urdf, L9v2-ROBOT) is
world -> prismatic vx, vy, vz (world axes) -> revolute vr, vp, vyaw about the successively rotated x, y, z axes
-> gripper base link (= G orientation, TCP at tcp_in_base). So base rotation R = Rx(r) Ry(p) Rz(y) and the
virtual joints are (base position, r, p, y) relative to the articulation root (the env origin).

Gimbal: p = asin(R[0, 2]) = asin(z_G . x). Each test turns the object about z (it stands upright on the ground) so
that the candidate's approach has no world-x component: p = 0 at the grasp, |p| <= the shake amplitude after.

Pure numpy."""
from __future__ import annotations

import math

import numpy as np

from ..sim import objv

BACKOFF = 0.06  # pre-grasp: T backed off along the approach (m)
LIFT = 0.10
SHAKE_DEG = 15.0
EMPTY_GAP = 0.003  # §12.12 EMPTY < 3 mm
CONTACT_TOL = 0.008  # §12.12 CONTACT = w_contact +- 8 mm
MIN_RISE = 0.05  # object >= 5 cm above the ground after the lift
MAX_SLIP = 0.01  # moved < 1 cm relative to the gripper during the shake
INSIDE_MARGIN = 0.01
WIDTH_EDGES = (0.03, 0.06)  # width classes narrow < 3 cm <= mid < 6 cm <= wide
FAMS = ("top", "oblique", "horizontal")


# ---------------------------------------------------------------------------------------------- rotations
def rx(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def ry(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def rz(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def rot_xyz(r, p, y):
    """Rotation of the virtual revolute chain: Rx(r) Ry(p) Rz(y) (intrinsic x, y', z'')."""
    return rx(r) @ ry(p) @ rz(y)


def _wrap_near(v, ref):
    return ref + (v - ref + math.pi) % (2 * math.pi) - math.pi


def euler_xyz(R, ref=None):
    """(r, p, y) with rot_xyz(r, p, y) = R, p in [-pi/2, pi/2]; r and y unwrapped to the nearest of ref."""
    R = np.asarray(R, float)
    p = math.asin(max(-1.0, min(1.0, R[0, 2])))
    if abs(R[0, 2]) < 1 - 1e-9:
        r = math.atan2(-R[1, 2], R[2, 2])
        y = math.atan2(-R[0, 1], R[0, 0])
    else:  # gimbal: put everything in r
        r = math.atan2(R[2, 1], R[1, 1])
        y = 0.0
    if ref is not None:
        r, y = _wrap_near(r, ref[0]), _wrap_near(y, ref[2])
    return r, p, y


def pose(R, t) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, t
    return T


# ---------------------------------------------------------------------------------------------- test set-up
def yaw_for(a) -> float:
    """Object yaw (about z) that turns the approach a so its horizontal part points along +y (no x part)."""
    a = np.asarray(a, float)
    h = math.hypot(a[0], a[1])
    if h < 1e-6:
        return 0.0
    return math.pi / 2 - math.atan2(a[1], a[0])


def object_pose(row: dict, yaw: float, origin=(0.0, 0.0, 0.0), lift: float = 0.0):
    """Canonical (centre, quat) of the upright object standing on z = origin z, turned by yaw, and its USD rigid
    body (root) pose via objv.root_from_canonical."""
    c = np.asarray(origin, float) + [0.0, 0.0, float(row["height"]) / 2 + lift]
    q = objv.yaw_q(yaw)
    root, qr = objv.root_from_canonical(row, c, q)
    return c, np.asarray(q, float), np.asarray(root, float), np.asarray(qr, float)


def tcp_world(T_obj, yaw: float, centre) -> np.ndarray:
    """Candidate TCP pose (object canonical frame) -> world for an object at (centre, yaw)."""
    return pose(rz(yaw), centre) @ np.asarray(T_obj, float)


def backoff(T_tcp, d: float = BACKOFF) -> np.ndarray:
    """Pre-grasp: the TCP moved back by d against the approach (= along +z_G)."""
    T = np.array(T_tcp, float)
    T[:3, 3] = T[:3, 3] + d * T[:3, 2]
    return T


def base_from_tcp(T_tcp, tcp_in_base) -> np.ndarray:
    """Gripper base link pose from the TCP pose (tcp_in_base = TCP position in the base, no rotation)."""
    T = np.array(T_tcp, float)
    T[:3, 3] = T[:3, 3] - T[:3, :3] @ np.asarray(tcp_in_base, float)
    return T


def vjoints(T_base, origin=(0.0, 0.0, 0.0), ref=None) -> np.ndarray:
    """Virtual joints (vx, vy, vz, vr, vp, vyaw) that put the base link at T_base (articulation root at origin)."""
    r, p, y = euler_xyz(T_base[:3, :3], ref=None if ref is None else ref[3:])
    return np.array([*(np.asarray(T_base[:3, 3], float) - origin), r, p, y])


def fk(q, origin=(0.0, 0.0, 0.0)) -> np.ndarray:
    return pose(rot_xyz(q[3], q[4], q[5]), np.asarray(q[:3], float) + origin)


def shake_rot(t: float, dur: float, deg: float = SHAKE_DEG, cycles: int = 2) -> np.ndarray:
    """World rotation of the shake at time t in [0, dur]: first half about world x, second half about world y,
    `cycles` sine periods each with amplitude deg."""
    half = dur / 2
    amp = math.radians(deg)
    if t < half:
        return rx(amp * math.sin(2 * math.pi * cycles * t / half))
    t2 = min(t - half, half)
    return ry(amp * math.sin(2 * math.pi * cycles * t2 / half))


def about_point(T, Rw, c) -> np.ndarray:
    """Pose T rotated by the world rotation Rw about the world point c."""
    c = np.asarray(c, float)
    return pose(Rw @ T[:3, :3], c + Rw @ (T[:3, 3] - c))


# ---------------------------------------------------------------------------------------------- batch plan
# timeline (s) of one test: settle, straight approach, close + settle, lift, hold, shake
PHASES = (("settle", 0.2), ("approach", 0.5), ("close", 1.1), ("lift", 0.5), ("hold", 2.0), ("shake", 1.5))


def euler_batch(R, ref=None) -> np.ndarray:
    """(N, 3) euler_xyz of (N, 3, 3) rotations away from the gimbal (|p| < 90 deg), unwrapped near ref (N, 3)."""
    R = np.asarray(R, float)
    p = np.arcsin(np.clip(R[:, 0, 2], -1.0, 1.0))
    r = np.arctan2(-R[:, 1, 2], R[:, 2, 2])
    y = np.arctan2(-R[:, 0, 1], R[:, 0, 0])
    out = np.stack([r, p, y], 1)
    if ref is not None:
        ref = np.asarray(ref, float)
        out[:, [0, 2]] = ref[:, [0, 2]] + (out[:, [0, 2]] - ref[:, [0, 2]] + math.pi) % (2 * math.pi) - math.pi
    return out


def plan_round(Tw, origins, tcp_in_base, dt: float, backoff_d: float = BACKOFF, lift: float = LIFT,
               shake_deg: float = SHAKE_DEG, cycles: int = 2):
    """Virtual joint targets (K, N, 6) of one round for N grasp poses Tw (N, 4, 4) (TCP, world) of grippers whose
    articulation roots stand at origins (N, 3), and the step index where each phase starts {name: k}."""
    Tw = np.asarray(Tw, float)
    origins = np.asarray(origins, float)
    N = len(Tw)
    R = Tw[:, :3, :3]
    tb = np.asarray(tcp_in_base, float)
    pg = Tw[:, :3, 3] - R @ tb  # base position at the grasp
    zg = R[:, :, 2]
    e0 = euler_batch(R)
    starts, ks = {}, 0
    steps = []
    for name, dur in PHASES:
        starts[name] = ks
        n = int(round(dur / dt))
        for j in range(n):
            s = (j + 1) / n
            if name == "settle":
                p, e = pg + backoff_d * zg, e0
            elif name == "approach":
                p, e = pg + backoff_d * (1 - s) * zg, e0
            elif name == "close":
                p, e = pg, e0
            elif name == "lift":
                sm = s * s * (3 - 2 * s)
                p, e = pg + [0.0, 0.0, lift * sm], e0
            elif name == "hold":
                p, e = pg + [0.0, 0.0, lift], e0
            else:
                Rw = shake_rot(j * dt, dur, shake_deg, cycles)
                c = Tw[:, :3, 3] + [0.0, 0.0, lift]  # TCP after the lift
                pb = pg + [0.0, 0.0, lift]
                p = c + (pb - c) @ Rw.T
                e = euler_batch(Rw[None] @ R, ref=e0)
            steps.append(np.concatenate([p - origins, e], 1))
        ks += n
    starts["end"] = ks
    return np.asarray(steps).reshape(ks, N, 6), starts


# ---------------------------------------------------------------------------------------------- collider override
SDF_RES = 256
CD = {"max_hulls": 64, "hull_verts": 64, "voxel_res": 1_000_000, "error_pct": 1.0}


def apply_collider(stage, prim_path: str, row_or_mode) -> int:
    """(pod, pxr) Replace the physics collider of a spawned mesh object (prim_path = its USD root) by its render
    meshes: mode 'sdf' (PhysX SDF triangle mesh, resolution SDF_RES) or 'cd' (fine convex decomposition, CD).
    The explicit collider meshes of the physics USD are switched off. row_or_mode: a catalog row (uses
    row['collider'], absent -> nothing changes) or the mode string. -> number of render meshes made colliders."""
    mode = row_or_mode.get("collider") if isinstance(row_or_mode, dict) else row_or_mode
    if not mode or mode == "none":
        return 0
    if mode not in ("sdf", "cd"):
        raise ValueError(f"collider mode {mode!r}")
    from pxr import PhysxSchema, Usd, UsdGeom, UsdPhysics
    root = stage.GetPrimAtPath(prim_path)
    if not root or not root.IsValid():
        raise ValueError(f"no prim {prim_path}")
    n = 0
    for p in Usd.PrimRange(root):
        if not p.IsA(UsdGeom.Mesh):
            continue
        if p.HasAPI(UsdPhysics.CollisionAPI):
            UsdPhysics.CollisionAPI(p).CreateCollisionEnabledAttr().Set(False)
            continue
        if UsdGeom.Imageable(p).ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        UsdPhysics.CollisionAPI.Apply(p)
        mc = UsdPhysics.MeshCollisionAPI.Apply(p)
        if mode == "sdf":
            mc.CreateApproximationAttr().Set("sdf")
            PhysxSchema.PhysxSDFMeshCollisionAPI.Apply(p).CreateSdfResolutionAttr().Set(SDF_RES)
        else:
            mc.CreateApproximationAttr().Set("convexDecomposition")
            c = PhysxSchema.PhysxConvexDecompositionCollisionAPI.Apply(p)
            c.CreateMaxConvexHullsAttr().Set(CD["max_hulls"])
            c.CreateHullVertexLimitAttr().Set(CD["hull_verts"])
            c.CreateVoxelResolutionAttr().Set(CD["voxel_res"])
            c.CreateErrorPercentageAttr().Set(CD["error_pct"])
            c.CreateShrinkWrapAttr().Set(True)
        n += 1
    return n


# ---------------------------------------------------------------------------------------------- gripper width
def width_to_q(w, table) -> float:
    W, Q = np.asarray(table["width_m"], float), np.asarray(table["drive_q"], float)
    o = np.argsort(W)
    return float(np.interp(float(w), W[o], Q[o]))


# The FFW-SG2 (RH-P12-RN) pads move on an arc: closing lowers them along the approach. Drop of the pads (m, along
# the approach) against the open hand (the TCP = pad centre at q = 0), from the URDF collision meshes
# (tools/l9/gtest_fingerprobe.py: lowest finger point per drive q, all four finger joints = q).
PAD_DROP = {"ffw_sg2": {"q": [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0, 1.1],
                        "dz": [0.0, 0.0092, 0.0170, 0.0229, 0.0268, 0.0279, 0.0284, 0.0284]}}


def pad_drop_q(q, grip: str):
    d = PAD_DROP.get(grip)
    if d is None:
        return np.zeros_like(np.asarray(q, float))
    return np.interp(np.asarray(q, float), d["q"], d["dz"])


_TABLES = {}


def width_table(grip: str):
    """width_to_joint of the gripper json (assets9/grippers, grasp9.JSON_NAME), None when there is none."""
    if grip not in _TABLES:
        import json
        import os
        from . import grasp9 as G
        p = os.path.join(G.DIR, G.JSON_NAME.get(grip, grip) + ".json")
        _TABLES[grip] = json.load(open(p, encoding="utf-8")).get("width_to_joint") if os.path.exists(p) else None
    return _TABLES[grip]


def pad_drop(w, grip: str, table=None) -> float:
    """Pad drop (m) when the hand is closed to the pad gap w (0 for grippers without a PAD_DROP entry)."""
    if grip not in PAD_DROP:
        return 0.0
    table = table or width_table(grip)
    return float(pad_drop_q(width_to_q(w, table), grip))


def exec_pose(T, w, grip: str, table=None) -> np.ndarray:
    """Hand TCP pose to command for a candidate T (4x4, TCP = contact centre, any frame) of contact width w (m):
    T backed off along the approach (+z_G) by the pad drop at w, so the closed pads meet the object at the planned
    contacts. Same frame as T."""
    return backoff(T, pad_drop(w, grip, table))


def q_to_width(q, table):
    W, Q = np.asarray(table["width_m"], float), np.asarray(table["drive_q"], float)
    o = np.argsort(Q)
    return np.interp(np.asarray(q, float), Q[o], W[o])


# ---------------------------------------------------------------------------------------------- candidates
def width_class(w) -> str:
    return "narrow" if w < WIDTH_EDGES[0] else ("mid" if w < WIDTH_EDGES[1] else "wide")


def fam_obj(a) -> str:
    th = math.degrees(math.acos(max(-1.0, min(1.0, -float(a[2])))))
    return "top" if th < 25.0 else ("oblique" if th < 65.0 else "horizontal")


HOLLOW_WORDS = ("cup", "mug", "bowl", "glass", "vase", "pot", "jar", "basket", "bucket", "pitcher")


def parts(row: dict, c1, c2, w) -> np.ndarray:
    """Grasped part per candidate (grasp9.part_of with the hollow / elongated rule of rt9)."""
    from . import grasp9 as G
    he = np.asarray(row.get("half_extents", (0.03, 0.03, 0.05)), float)
    cat = f"{row.get('category', '')} {row.get('name', '')}".lower()
    hollow = bool(row.get("inside")) or any(x in cat for x in HOLLOW_WORDS)
    elong = float(max(he[:2])) > 2.5 * float(min(he[:2]))
    return np.array([G.part_of(c1[i], c2[i], float(w[i]), he, hollow, elong) for i in range(len(w))], dtype=object)


def natural_rank(row: dict) -> dict:
    """{(object-frame family, part): rank} of the row's natural order (side / front -> horizontal)."""
    from . import grasp9 as G
    order = G.natural_order(f"{row.get('category', '')} {row.get('name', '')}", float(row.get("height", 0.1)))
    out = {}
    for r, (f, p) in enumerate(order):
        out.setdefault(("horizontal" if f in ("side", "front") else f, p), r)
    return out


def pick(a, w, score, n: int = 48, part=None, prefer=None) -> np.ndarray:
    """Indices of at most n candidates spread over (family x part x width class): round robin over the groups
    (groups of the natural order `prefer` {(family, part): rank} first), each group in descending score."""
    a, w, score = np.asarray(a, float).reshape(-1, 3), np.asarray(w, float), np.asarray(score, float)
    if len(w) <= n:
        return np.arange(len(w))
    part = ["body"] * len(w) if part is None else list(part)
    prefer = prefer or {}
    keys = [(fam_obj(a[i]), part[i], width_class(w[i])) for i in range(len(w))]
    groups = {}
    for i in np.argsort(-score, kind="stable"):
        groups.setdefault(keys[i], []).append(int(i))
    order = [groups[k] for k in sorted(groups, key=lambda k: (prefer.get(k[:2], 99), k))]
    out = []
    while len(out) < n:
        moved = False
        for g in order:
            if g and len(out) < n:
                out.append(g.pop(0))
                moved = True
        if not moved:
            break
    return np.sort(np.asarray(out, int))


# ---------------------------------------------------------------------------------------------- verdict
def gap_class(gap: float, w: float) -> str:
    if gap < EMPTY_GAP:
        return "EMPTY"
    return "CONTACT" if abs(gap - w) <= CONTACT_TOL else "WIDE"


def inside(p_G, pad_w: float, max_open: float, pad_z) -> bool:
    """Grasp centre (in the TCP frame) still between the two fingers."""
    x, y, z = (float(v) for v in p_G)
    return (abs(x) <= pad_w / 2 + INSIDE_MARGIN and abs(y) <= max_open / 2
            and pad_z[0] - INSIDE_MARGIN <= z <= pad_z[1] + INSIDE_MARGIN)


def held(rise: float, inside_ok: bool, gap: float) -> bool:
    return bool(rise >= MIN_RISE and inside_ok and gap >= EMPTY_GAP)


def verdict(rise_hold, in_hold, gap_hold, rise_end, in_end, gap_end, slip) -> dict:
    lift_ok = held(rise_hold, in_hold, gap_hold)
    shake_ok = bool(lift_ok and held(rise_end, in_end, gap_end) and slip < MAX_SLIP)
    return {"lift_ok": lift_ok, "shake_ok": shake_ok}
