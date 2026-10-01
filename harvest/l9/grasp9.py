"""L9 v2 grasp candidates (spec §12.4, label rule §12.8; research grasp_point_learning_2026-10-02 §11.6-11.9). Pure numpy.

Frames
  object  = the canonical frame of harvest/sim/objv.py (bbox centre of the upright object, z up); meshes come from
            tools/l9/mesh_export.py in this frame; the support plane of an upright object is z = -h/2.
  G       = the gripper TCP frame, = the AI Worker EE convention of the L8S executor: z_G = -a (a = approach
            direction, the way the hand moves in), y_G = closing axis (fingers move along +-y), x_G = y_G x z_G.
            A top-down grasp at yaw 0 is the identity rotation. TCP = midpoint between the two pad centres.

Candidate generation (analytic antipodal, QuickGrasp / ACRONYM style):
  surface points (area weighted) -> rays along +-normal -> every hit q_k along the ray is a pair (p, q_k) when
  (i) width 2 mm <= |q - p| <= max_open - 1 cm, (ii) the axis is inside the friction cone at both contacts
  (|cos| >= cos(atan MU)), (iii) a finger fits behind p and beyond q (free ray length >= finger thickness): this keeps
  outer grasps (both outer walls of a cup) and wall pinches (one finger inside a hollow, one outside) and drops
  'squeeze air' pairs. Each pair gives approach directions every 15 deg around the axis; from below is dropped.
  Then the swept gripper (fingers at the pre-shape opening + palm, extended back along -a to the stand-off) must not
  hit the object, and the fingertips must stay SUPPORT_CLEAR above the support plane.
The Isaac lift + shake test (tools/l9/grasp_test.py) and cuRobo reach decide which candidates are valid."""
from __future__ import annotations

import json
import math
import os

import numpy as np

MU = 0.4  # friction cone half angle atan(0.4) = 21.8 deg (spec §12.4)
W_MIN = 0.002
OPEN_MARGIN = 0.010  # width <= max_open - 1 cm
PRE_OPEN = (0.015, 0.04)  # pre-shape = width + U[1.5, 4] cm, clipped to max_open (spec §12.5)
BELOW_Z = 0.26  # approach vectors with z > +0.26 come from below: dropped
STEP_DEG = 15.0
STANDOFF = 0.14  # swept-volume length behind the final pose (pre-grasp stand-off 8-14 cm)
SUPPORT_CLEAR = 0.004
FAMILIES = ("top", "oblique", "front", "side")
TOP_DEG, OBL_DEG, FRONT_DEG = 25.0, 65.0, 45.0
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9", "grippers")

# Coarse gripper models (boxes in G). Defaults are hypotheses until the L9v2-ROBOT gripper json exists (it wins).
#   max_open, pad_len (along a), finger_t (along y, behind the pad face), finger_w (along x), finger_len (tip ->
#   knuckle along -a from the tip), palm = (x, y, z) half sizes of the palm box above the knuckles.
_DEFAULTS = {
    "ffw_sg2": {"max_open": 0.107, "pad_len": 0.030, "finger_t": 0.012, "finger_w": 0.022, "finger_len": 0.060,
                "palm_half": (0.035, 0.075, 0.035), "source": "default (RH-P12-RN datasheet-like, hypothesis)"},
    "franka": {"max_open": 0.080, "pad_len": 0.018, "finger_t": 0.010, "finger_w": 0.020, "finger_len": 0.054,
               "palm_half": (0.030, 0.100, 0.030), "source": "default (franka_description hand, hypothesis)"},
}


def gripper(name: str) -> dict:
    p = os.path.join(DIR, name + ".json")
    g = dict(_DEFAULTS.get(name, _DEFAULTS["ffw_sg2"]))
    if os.path.exists(p):
        g.update(json.load(open(p, encoding="utf-8")))
    g["name"] = name
    return g


# ---------------------------------------------------------------------------------------------- geometry helpers
def qmat(q) -> np.ndarray:
    w, x, y, z = (float(v) for v in q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def mat_quat(R) -> np.ndarray:
    R = np.asarray(R, float)
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = [(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = [(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = [(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s]
    q = np.asarray(q, float)
    q = q / np.linalg.norm(q)
    return q if q[0] >= 0 else -q


def yaw_quat(yaw: float) -> np.ndarray:
    return np.array([math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)])


def cup_mesh(r_out: float, wall: float, h: float, n: int = 48):
    """Closed hollow cylinder with a bottom of thickness `wall`, centred like the canonical frame (z in [-h/2, h/2]).
    Test / primitive helper."""
    r_in, z0, z1 = r_out - wall, -h / 2, h / 2
    zb = z0 + wall
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    ring = lambda r, z: np.stack([r * np.cos(ang), r * np.sin(ang), np.full(n, z)], 1)
    V = np.concatenate([ring(r_out, z0), ring(r_out, z1), ring(r_in, z1), ring(r_in, zb),
                        [[0, 0, z0], [0, 0, zb]]])
    o0, o1, i1, i0, cb, ci = 0, n, 2 * n, 3 * n, 4 * n, 4 * n + 1
    F = []
    for k in range(n):
        j = (k + 1) % n
        F += [[o0 + k, o0 + j, o1 + j], [o0 + k, o1 + j, o1 + k]]  # outer wall
        F += [[o1 + k, o1 + j, i1 + j], [o1 + k, i1 + j, i1 + k]]  # rim
        F += [[i1 + k, i1 + j, i0 + j], [i1 + k, i0 + j, i0 + k]]  # inner wall
        F += [[cb, o0 + j, o0 + k], [ci, i0 + k, i0 + j]]  # bottom outside, inner floor
    return V, np.asarray(F, int)


def face_normals(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a, 1e-15)[:, None], a / 2


def sample_surface(V, F, n: int, rng):
    N, A = face_normals(V, F)
    ok = A > 1e-12
    idx = np.flatnonzero(ok)
    f = rng.choice(idx, size=n, p=A[ok] / A[ok].sum())
    u, v = rng.random(n), rng.random(n)
    m = u + v > 1
    u[m], v[m] = 1 - u[m], 1 - v[m]
    P = V[F[f, 0]] + u[:, None] * (V[F[f, 1]] - V[F[f, 0]]) + v[:, None] * (V[F[f, 2]] - V[F[f, 0]])
    return P, N[f], f


def ray_hits(O, D, V, F, eps: float = 1e-4, chunk: int = 128, faces: bool = False):
    """Sorted hit distances (> eps) of each ray (O[i] + t D[i]) with the triangle mesh (Moller-Trumbore, both
    faces); faces=True also returns the hit face ids."""
    v0, e1, e2 = V[F[:, 0]], V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]
    out, outf = [], []
    for s in range(0, len(O), chunk):
        o, d = O[s:s + chunk, None, :], D[s:s + chunk, None, :]
        pv = np.cross(d, e2[None])
        det = (e1[None] * pv).sum(-1)
        good = np.abs(det) > 1e-12
        inv = np.where(good, 1.0 / np.where(good, det, 1.0), 0.0)
        tv = o - v0[None]
        u = (tv * pv).sum(-1) * inv
        hit = good & (u >= 0) & (u <= 1)
        qv = np.cross(tv, e1[None])
        v = (d * qv).sum(-1) * inv
        t = (e2[None] * qv).sum(-1) * inv
        hit &= (v >= 0) & (u + v <= 1) & (t > eps)
        for i in range(hit.shape[0]):
            fi = np.flatnonzero(hit[i])
            ts = t[i][fi]
            o_ = np.argsort(ts)
            ts, fi = ts[o_], fi[o_]
            if len(ts) > 1:  # merge duplicates (shared edges / double faces)
                k = np.concatenate([[True], np.diff(ts) > 2e-4])
                ts, fi = ts[k], fi[k]
            out.append(ts)
            outf.append(fi)
    return (out, outf) if faces else out


def downsample(P: np.ndarray, cell: float) -> np.ndarray:
    k = np.floor(P / cell).astype(np.int64)
    _, i = np.unique(k, axis=0, return_index=True)
    return P[np.sort(i)]


# ---------------------------------------------------------------------------------------------- antipodal pairs
def antipodal_pairs(V, F, gr: dict, n: int = 3000, seed: int = 0) -> dict:
    """Antipodal contact pairs (rules in the module doc), de-duplicated per (2 mm centre, ~8 deg axis) cell."""
    V, F = np.asarray(V, float), np.asarray(F, int)
    rng = np.random.default_rng(seed)
    P, N, _ = sample_surface(V, F, n, rng)
    Nf, _ = face_normals(V, F)
    cos_c = math.cos(math.atan(MU))
    wmax = gr["max_open"] - OPEN_MARGIN
    ft = gr["finger_t"]
    O = np.concatenate([P, P])
    D = np.concatenate([N, -N])
    fwd, fwdf = ray_hits(O, D, V, F, faces=True)
    back = ray_hits(O, -D, V, F)
    ps, qs, ws, angs = [], [], [], []
    for i in range(len(O)):
        ts = fwd[i]
        if len(ts) == 0 or ts[0] > wmax:
            continue
        if len(back[i]) and back[i][0] < ft:
            continue
        d = D[i]
        cp = abs(float(N[i % n] @ d))
        if cp < cos_c:
            continue
        cq_all = np.abs(Nf[fwdf[i]] @ d)
        room = np.append(np.diff(ts), np.inf)
        for k in np.flatnonzero((ts >= W_MIN) & (ts <= wmax) & (room >= ft) & (cq_all >= cos_c)):
            ps.append(O[i])
            qs.append(O[i] + ts[k] * d)
            ws.append(ts[k])
            angs.append((math.acos(min(cp, 1.0)), math.acos(min(float(cq_all[k]), 1.0))))
    if not ps:
        z = np.zeros((0, 3))
        return {"p": z, "q": z, "w": np.zeros(0), "ang": np.zeros((0, 2))}
    p, q, w, ang = np.asarray(ps), np.asarray(qs), np.asarray(ws), np.asarray(angs)
    ax = (q - p) / w[:, None]
    flip = (ax[:, 0] < 0) | ((ax[:, 0] == 0) & (ax[:, 1] < 0))
    ax = np.where(flip[:, None], -ax, ax)
    key = np.concatenate([np.round((p + q) / 2 / 0.002), np.round(ax / 0.14)], 1).astype(np.int64)
    _, keep = np.unique(key, axis=0, return_index=True)
    keep = np.sort(keep)
    return {"p": p[keep], "q": q[keep], "w": w[keep], "ang": ang[keep]}


# ---------------------------------------------------------------------------------------------- poses, collision
def frame_of(a, c) -> np.ndarray:
    """Rotation (columns x_G, y_G, z_G) for approach a and closing axis c (c is made orthogonal to a)."""
    a = np.asarray(a, float) / np.linalg.norm(a)
    c = np.asarray(c, float) - a * float(np.dot(a, c))
    c = c / np.linalg.norm(c)
    z = -a
    x = np.cross(c, z)
    return np.stack([x, c, z], 1)


def boxes(gr: dict, open_w: float, standoff: float = 0.0):
    """Gripper boxes in G (centre, half sizes): two fingers at the given opening + the palm; standoff > 0 extends
    them back along +z_G (the swept volume of the straight approach)."""
    pl, ft, fw, fl = gr["pad_len"], gr["finger_t"], gr["finger_w"], gr["finger_len"]
    tip = -pl / 2  # fingertips: half a pad beyond the TCP along a (= -z_G)
    knuckle = tip + fl
    out = []
    for s in (-1, 1):
        y = s * (open_w / 2 + ft / 2)
        z0, z1 = tip, knuckle + standoff
        out.append((np.array([0.0, y, (z0 + z1) / 2]), np.array([fw / 2, ft / 2, (z1 - z0) / 2])))
    ph = np.asarray(gr["palm_half"], float)
    z0, z1 = knuckle, knuckle + 2 * ph[2] + standoff
    out.append((np.array([0.0, 0.0, (z0 + z1) / 2]), np.array([ph[0], ph[1], (z1 - z0) / 2])))
    return out


def hits_boxes(pts_G: np.ndarray, bx) -> bool:
    for c, h in bx:
        if (np.abs(pts_G - c) <= h).all(1).any():
            return True
    return False


def lowest_point(T: np.ndarray, gr: dict, open_w: float) -> float:
    """Lowest z (object frame) of the gripper boxes at the final pose (no stand-off)."""
    return _lowest(T, boxes(gr, open_w))


def sample_grasps(V, F, grip: str, seed: int = 0, n_surface: int = 3000, cap: int = 400,
                  support_z: float | None = None, max_pairs: int = 1500) -> dict:
    """All candidates of one object for one gripper, object frame. support_z defaults to the mesh bottom."""
    V, F = np.asarray(V, float), np.asarray(F, int)
    gr = gripper(grip)
    rng = np.random.default_rng(seed + 7)
    pr = antipodal_pairs(V, F, gr, n=n_surface, seed=seed)
    if len(pr["w"]) > max_pairs:
        sel = np.sort(rng.choice(len(pr["w"]), max_pairs, replace=False))
        pr = {k: v[sel] for k, v in pr.items()}
    sz = float(V[:, 2].min()) if support_z is None else float(support_z)
    S, _, _ = sample_surface(V, F, 6000, np.random.default_rng(seed + 11))
    pts = downsample(np.concatenate([V, S]), 0.003)
    cos_c = math.cos(math.atan(MU))
    phis = np.radians(np.arange(0.0, 360.0, STEP_DEG))
    T_l, c1, c2, w_l, a_l, sc, pre = [], [], [], [], [], [], []
    for p, q, w, ang in zip(pr["p"], pr["q"], pr["w"], pr["ang"]):
        c = (q - p) / w
        m = (p + q) / 2
        u = np.cross(c, [0.0, 0.0, 1.0])
        if np.linalg.norm(u) < 1e-6:
            u = np.cross(c, [1.0, 0.0, 0.0])
        u /= np.linalg.norm(u)
        v = np.cross(c, u)
        A = np.cos(phis)[:, None] * u + np.sin(phis)[:, None] * v  # (24, 3)
        A = A[A[:, 2] <= BELOW_Z]
        if not len(A):
            continue
        open_w = min(w + rng.uniform(*PRE_OPEN), gr["max_open"])
        bx_low = boxes(gr, open_w)
        bx = boxes(gr, max(open_w, w + 0.002), STANDOFF)
        cone = min(1 - (1 - math.cos(ang[0])) / (1 - cos_c), 1 - (1 - math.cos(ang[1])) / (1 - cos_c))
        rel = pts - m
        for a in A:
            R = frame_of(a, c)
            T = np.eye(4)
            T[:3, :3], T[:3, 3] = R, m
            if _lowest(T, bx_low) < sz + SUPPORT_CLEAR:
                continue
            if hits_boxes(rel @ R, bx):
                continue
            T_l.append(T)
            c1.append(p)
            c2.append(q)
            w_l.append(w)
            a_l.append(a)
            pre.append(open_w)
            sc.append(max(cone, 0.0) * math.exp(-float(np.linalg.norm(m)) / 0.04))
    K = len(T_l)
    out = {"T": np.asarray(T_l).reshape(K, 4, 4), "c1": np.asarray(c1).reshape(K, 3), "c2": np.asarray(c2).reshape(K, 3),
           "w": np.asarray(w_l), "a": np.asarray(a_l).reshape(K, 3), "score": np.asarray(sc),
           "pre_open": np.asarray(pre), "gripper": gr, "source": np.array(["analytic"] * K)}
    if K > cap:
        out = thin(out, cap, seed)
    return out


_CORNERS = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float)


def _lowest(T, bx) -> float:
    return min(float(((_CORNERS * h + c) @ T[:3, :3].T + T[:3, 3])[:, 2].min()) for c, h in bx)


def thin(C: dict, cap: int, seed: int = 0) -> dict:
    """Keep at most `cap` candidates: best score per (5 mm centre, 15 deg approach, 15 deg axis) cell, then the cells
    in a seeded order that spreads over families and widths."""
    m = (C["c1"] + C["c2"]) / 2
    ax = (C["c2"] - C["c1"]) / np.maximum(C["w"], 1e-9)[:, None]
    ax = np.where(ax[:, [0]] < 0, -ax, ax)
    key = np.concatenate([np.round(m / 0.005), np.round(C["a"] / 0.26), np.round(ax / 0.26)], 1)
    order = np.argsort(-C["score"], kind="stable")
    seen, keep = set(), []
    for i in order:
        k = tuple(key[i].astype(int))
        if k in seen:
            continue
        seen.add(k)
        keep.append(i)
    keep = np.asarray(keep)
    if len(keep) > cap:
        rng = np.random.default_rng(seed)
        fam = np.array([family_obj(a) for a in C["a"][keep]])
        pick = []
        groups = [keep[fam == f] for f in ("top", "oblique", "horizontal")]
        groups = [list(rng.permutation(g)) for g in groups]
        while len(pick) < cap and any(groups):
            for g in groups:
                if g and len(pick) < cap:
                    pick.append(g.pop())
        keep = np.asarray(pick)
    return {k: (v[keep] if isinstance(v, np.ndarray) and len(v) == len(C["w"]) else v) for k, v in C.items()}


def family_obj(a) -> str:
    th = math.degrees(math.acos(max(-1.0, min(1.0, -float(a[2])))))
    return "top" if th < TOP_DEG else ("oblique" if th < OBL_DEG else "horizontal")


def family(a_world, f_dir) -> str:
    """Approach family in the robot base frame (spec §12.8): angle to straight down; horizontal ones split by the
    angle to the base->object horizontal direction f_dir."""
    a = np.asarray(a_world, float) / np.linalg.norm(a_world)
    th = math.degrees(math.acos(max(-1.0, min(1.0, -a[2]))))
    if th < TOP_DEG:
        return "top"
    if th < OBL_DEG:
        return "oblique"
    h = a[:2] / max(np.linalg.norm(a[:2]), 1e-9)
    f = np.asarray(f_dir, float)[:2]
    f = f / max(np.linalg.norm(f), 1e-9)
    return "front" if math.degrees(math.acos(max(-1.0, min(1.0, float(h @ f))))) < FRONT_DEG else "side"


def to_world(C: dict, pos, quat) -> dict:
    R, t = qmat(quat), np.asarray(pos, float)
    W = dict(C)
    T = C["T"].copy()
    T[:, :3, :3] = R[None] @ C["T"][:, :3, :3]
    T[:, :3, 3] = C["T"][:, :3, 3] @ R.T + t
    W["T"] = T
    W["c1"] = C["c1"] @ R.T + t
    W["c2"] = C["c2"] @ R.T + t
    W["a"] = C["a"] @ R.T
    return W


def project(K, R_cw, t_cw, X):
    """Pixels of world points X for a pinhole camera with optical frame rotation R_cw (columns = optical x, y, z in
    world) and centre t_cw. Returns (N, 2) and the depth."""
    Xc = (np.atleast_2d(X) - t_cw) @ R_cw
    z = Xc[:, 2]
    uv = (Xc[:, :2] / np.maximum(z, 1e-9)[:, None]) * [K[0, 0], K[1, 1]] + [K[0, 2], K[1, 2]]
    return uv, z


def rot_img(m, c, K, R_cw, t_cw, half: float = 0.02):
    """Angle (deg, folded to [0, 180)) of the closing axis c at m projected into the image, and its 15 deg bin."""
    uv, _ = project(K, R_cw, t_cw, np.stack([m - half * c, m + half * c]))
    du, dv = uv[1] - uv[0]
    deg = math.degrees(math.atan2(dv, du)) % 180.0
    return deg, int(deg // 15.0) % 12


def rot_base(a, c):
    """Closing-axis angle (deg, [0, 180)) about the approach axis in the robot base frame: for a near-vertical
    approach the yaw of c; otherwise measured from the horizontal reference a x z."""
    a, c = np.asarray(a, float), np.asarray(c, float)
    if abs(a[2]) > math.cos(math.radians(TOP_DEG)):
        deg = math.degrees(math.atan2(c[1], c[0])) % 180.0
    else:
        ref = np.cross(a, [0.0, 0.0, 1.0])
        ref /= np.linalg.norm(ref)
        up = np.cross(ref, a)
        deg = math.degrees(math.atan2(float(c @ up), float(c @ ref))) % 180.0
    return deg, int(deg // 15.0) % 12


# ---------------------------------------------------------------------------------------------- label rule
FAMILY_ORDER = {None: ("top", "oblique", "front", "side"),
                "blocked_above": ("front", "side", "oblique"),
                "tall": ("front", "side", "oblique", "top"),
                "flat": ("top", "oblique"),
                "wide_hollow": ("top", "oblique"),
                "handle": ("side", "front", "oblique", "top")}
NEIGHBOURS = {"top": ("oblique", "front", "side"), "oblique": ("top", "front", "side"),
              "front": ("oblique", "side", "top"), "side": ("oblique", "front", "top")}
TOP_CENTRE_R = 0.012


def select_label(fam, centre_d, robot_d, margin, ok, constraint=None, instructed=None, handle_pen=None):
    """Deterministic label rule (label_rule deterministic_v1). fam / centre_d (grasp centre to object axis, m) /
    robot_d (grasp centre to robot base, m) / margin (reach margin) / ok (valid: test passed + reachable) per
    candidate. -> (index | None, rule_step, approach_reason).
      0) top-centre valid -> it (closest to the centre);  1) a scene constraint fixes the family order;
      2) inside the family: robot side (2 cm steps) -> away from a handle -> largest reach margin."""
    fam = np.asarray(fam)
    ok = np.asarray(ok, bool)
    hp = np.zeros(len(fam)) if handle_pen is None else np.asarray(handle_pen, float)

    def best(mask):
        idx = np.flatnonzero(mask & ok)
        if len(idx) == 0:
            return None
        key = sorted(idx, key=lambda i: (round(float(robot_d[i]) / 0.02), hp[i], -float(margin[i]), i))
        return int(key[0])

    if instructed is not None:
        i = best(fam == instructed)
        return (i, 2, "instructed") if i is not None else (None, 2, "instructed")
    if constraint is None:
        tc = np.flatnonzero((fam == "top") & ok & (np.asarray(centre_d) <= TOP_CENTRE_R))
        if len(tc):
            return int(tc[np.argmin(np.asarray(centre_d)[tc])]), 0, "default"
    for f in FAMILY_ORDER.get(constraint, FAMILY_ORDER[None]):
        i = best(fam == f)
        if i is not None:
            return i, (1 if constraint else 2), (f"scene_constraint:{constraint}" if constraint else "default")
    return None, 2, (f"scene_constraint:{constraint}" if constraint else "default")


def fallback_order(fam: str, rot_bin: int) -> list:
    """Execution fallback (spec §12.8): same family rot +-1, +-2 bins -> neighbour families (any rot, closest first)
    -> stop."""
    out = [(fam, rot_bin)]
    for d in (1, 2):
        out += [(fam, (rot_bin - d) % 12), (fam, (rot_bin + d) % 12)]
    for f in NEIGHBOURS[fam]:
        out.append((f, None))
    return out
