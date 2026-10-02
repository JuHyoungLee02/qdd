"""L9 live (no-cache) executor: antipodal grasp search directly on an OBSERVED point cloud, for objects with no
precomputed candidate cache (user principle 10-02: a per-object cache does not generalise to new objects; the VLM's
point + approach family + rotation bin carries the fine decision, the executor only has to refine near that point
from what the depth camera actually sees). Pure numpy -- mirrors grasp9.py's pose / collision geometry (frame_of,
boxes, hits_boxes, lowest_point / _lowest, family, rot_base / rot_img, obb_overlap, thin) exactly, so a candidate
built here is a drop-in v2plan.GraspChoice: rt9.Runtime's motion planning (_approach_plan, TrajExec, next_fallback,
pick_record) needs no change to execute it (harvest/l9/rtlive9.py: LiveRuntime, the opt-in subclass that wires this
into the collection loop).

Pipeline (spec steps 2-5 of the live-executor task; step 1 = the VLM command, out of this module's scope):
  back_project   -> the commanded 2D point (0-1000 image scale) + that camera's own depth = a base-frame 3D point
  crop_cloud     -> small region of the observed cloud (head depth, + wrist depth when given) around that point
  estimate_normals -> local-PCA surface normal per cropped point (no mesh: the only normal source available)
  antipodal_pairs_cloud -> antipodal contact PAIRS directly on the point samples (same cone test as grasp9's
                     mesh version; the mesh's ray-cast 'free length' check is replaced by a nearest-neighbour
                     clearance test: no third observed point lies on the open segment between the two contacts)
  sample_grasps_cloud -> swept-gripper collision / support-clearance, restricted to the COMMANDED approach family
                     and rot bin (+-1): the point cloud never has to justify a full unconstrained grasp search,
                     only "is the VLM's suggestion actually free of the object and its neighbours".
  choose_live    -> the single best candidate (closest contact midpoint to the commanded point) as a GraspChoice,
                     or calls the learned refiner hook first when one is installed (`refine`, GraspGen-X later).

refine() hook: a callable with the signature `refine(cloud, point3d, approach, rot, gripper) -> candidates | None`
(candidates: a dict in the sample_grasps_cloud return shape, or None/empty to fall back to the antipodal search
here). `set_refiner` / `get_refiner` hold the process-wide hook; nothing calls GraspGen-X today (NVIDIA Open Model
License weights, internal use, licence cleared 2026-10-02) -- integrating it is a separate task."""
from __future__ import annotations

import math

import numpy as np

from . import grasp9 as G

CROP_R = 0.09           # crop radius (m) around the back-projected point: bigger than any pickable object's half-diag
NORMAL_K = 12           # neighbours for the local-PCA normal estimate
MIN_PTS = 30            # fewer points in the crop than this: no live search possible (occluded / off-screen point)
ROT_WIN = 1             # rot-bin tolerance: +-1 of the commanded bin (15 deg each -> +-15 deg), spec step 4
CLEAR_R = 0.004         # lateral radius for the "nothing blocks the closing path" pair-clearance check
MAX_CLOUD = 400         # the cloud is capped to this many points before the O(n^2) pair search
MAX_PAIRS_FOR_CLEAR = 4000  # the O(pairs x n) clearance loop is capped by subsampling pairs beyond this


# ---------------------------------------------------------------------------------------------- perception
def back_project(point_2d, cam, depth) -> np.ndarray | None:
    """0-1000 image point (the VLM's convention, astra_solo.resolve.to_scaled) -> base-frame 3D point from the
    camera's own depth map (astra_motion.geometry.lift_depth: falls back to a small-window median when the exact
    pixel's depth is invalid). None when even the window has no valid depth."""
    from ..astra_motion.geometry import lift_depth
    from ..astra_solo.resolve import to_pixel
    iu, iv = to_pixel(point_2d, cam.W, cam.H)
    p = lift_depth(cam, iu, iv, depth)
    return None if p is None else np.asarray(p, float)


def crop_cloud(point3d, head_cam, head_depth, wrist_cam=None, wrist_depth=None, radius: float = CROP_R) -> np.ndarray:
    """Base-frame points within `radius` of point3d, unprojected from the head depth (always) and the wrist depth
    (when both wrist_cam and wrist_depth are given -- the wrist is often closer and fills in what the head's angle
    misses). Invalid depth pixels (0 / inf / nan, astra_solo.resolve.depth_points) are dropped before the radius
    mask."""
    from ..astra_solo.resolve import depth_points
    point3d = np.asarray(point3d, float)
    pts = []
    for cam, depth in ((head_cam, head_depth), (wrist_cam, wrist_depth)):
        if cam is None or depth is None:
            continue
        P = depth_points(cam, depth).reshape(-1, 3)
        valid = np.isfinite(P).all(1)
        if not valid.any():
            continue
        P = P[valid]
        d = np.linalg.norm(P - point3d, axis=1)
        m = d <= radius
        if m.any():
            pts.append(P[m])
    return np.concatenate(pts, 0) if pts else np.zeros((0, 3))


def downsample_cap(P: np.ndarray, cap: int = MAX_CLOUD, seed: int = 0) -> np.ndarray:
    """A deterministic random subset of at most `cap` rows (the O(n^2) pair search below needs a bounded cloud)."""
    if len(P) <= cap:
        return P
    rng = np.random.default_rng(seed)
    return P[np.sort(rng.choice(len(P), cap, replace=False))]


def estimate_normals(P: np.ndarray, k: int = NORMAL_K) -> np.ndarray:
    """Local-PCA surface normal per point (eigenvector of the smallest eigenvalue of the k-nearest-neighbour
    covariance), oriented away from the crop's own centroid. Hypothesis (no mesh to check against): a single-object
    crop is small enough that "away from its own centre" is outward almost everywhere; a concave crop (e.g. deep
    inside a hollow object) can get this backwards at the few points nearest the concavity -- the antipodal cone
    test on BOTH contacts' normals then rejects most pairs this would have broken."""
    n = len(P)
    if n == 0:
        return np.zeros((0, 3))
    kk = min(k, n - 1)
    if kk < 2:
        return np.tile(np.array([0.0, 0.0, 1.0]), (n, 1))
    d2 = ((P[:, None, :] - P[None, :, :]) ** 2).sum(-1)
    idx = np.argsort(d2, axis=1)[:, 1:kk + 1]
    centre = P.mean(0)
    N = np.empty_like(P)
    for i in range(n):
        Q = P[idx[i]] - P[idx[i]].mean(0)
        cov = Q.T @ Q
        _, v = np.linalg.eigh(cov)
        nv = v[:, 0]
        nv = nv if nv @ (P[i] - centre) >= 0 else -nv
        N[i] = nv
    return N


# ---------------------------------------------------------------------------------------------- antipodal pairs
def _empty_pairs() -> dict:
    z = np.zeros((0, 3))
    return {"p": z, "q": z, "w": np.zeros(0), "ang": np.zeros((0, 2))}


def antipodal_pairs_cloud(P: np.ndarray, N: np.ndarray, gr: dict, seed: int = 0) -> dict:
    """Antipodal contact pairs directly on an observed point cloud (no mesh, no ray casting): candidate (i, j) with
    W_MIN <= |Pj - Pi| <= max_open - OPEN_MARGIN and both normals inside the friction cone of the connecting axis
    (identical test to grasp9.antipodal_pairs), then a clearance pass: no third cloud point sits within CLEAR_R of
    the OPEN segment strictly between the two contacts (the finite point-sample analogue of the mesh version's 'a
    finger fits behind p and beyond q' free-ray-length check)."""
    n = len(P)
    if n < 2:
        return _empty_pairs()
    cos_c = math.cos(math.atan(G.MU))
    wmax = gr["max_open"] - G.OPEN_MARGIN
    D = P[:, None, :] - P[None, :, :]
    dist = np.linalg.norm(D, axis=2)
    iu, ju = np.triu_indices(n, 1)
    w = dist[iu, ju]
    keep = (w >= G.W_MIN) & (w <= wmax)
    iu, ju, w = iu[keep], ju[keep], w[keep]
    if not len(iu):
        return _empty_pairs()
    axis = (P[ju] - P[iu]) / w[:, None]
    cos_i = np.abs((N[iu] * axis).sum(1))
    cos_j = np.abs((N[ju] * axis).sum(1))
    ok = (cos_i >= cos_c) & (cos_j >= cos_c)
    iu, ju, w, axis, cos_i, cos_j = iu[ok], ju[ok], w[ok], axis[ok], cos_i[ok], cos_j[ok]
    if not len(iu):
        return _empty_pairs()
    if len(iu) > MAX_PAIRS_FOR_CLEAR:  # bound the O(pairs x n) clearance loop below
        rng = np.random.default_rng(seed)
        sel = np.sort(rng.choice(len(iu), MAX_PAIRS_FOR_CLEAR, replace=False))
        iu, ju, w, axis, cos_i, cos_j = iu[sel], ju[sel], w[sel], axis[sel], cos_i[sel], cos_j[sel]
    clear = np.ones(len(iu), bool)
    for k in range(len(iu)):
        p, a_, ww = P[iu[k]], axis[k], w[k]
        t = (P - p) @ a_
        lat = np.linalg.norm((P - p) - t[:, None] * a_, axis=1)
        inside = (t > G.W_MIN) & (t < ww - G.W_MIN) & (lat < CLEAR_R)
        inside[iu[k]] = False
        inside[ju[k]] = False
        if inside.any():
            clear[k] = False
    iu, ju, w, axis, cos_i, cos_j = iu[clear], ju[clear], w[clear], axis[clear], cos_i[clear], cos_j[clear]
    if not len(iu):
        return _empty_pairs()
    ang = np.stack([np.arccos(np.clip(cos_i, -1, 1)), np.arccos(np.clip(cos_j, -1, 1))], 1)
    flip = (axis[:, 0] < 0) | ((axis[:, 0] == 0) & (axis[:, 1] < 0))
    axis = np.where(flip[:, None], -axis, axis)
    return {"p": P[iu], "q": P[ju], "w": w, "ang": ang}


# ---------------------------------------------------------------------------------------------- live candidates
def _empty_grasps(gr: dict) -> dict:
    z = np.zeros((0, 4, 4))
    return {"T": z, "c1": np.zeros((0, 3)), "c2": np.zeros((0, 3)), "w": np.zeros(0), "a": np.zeros((0, 3)),
            "score": np.zeros(0), "pre_open": np.zeros(0), "gripper": gr, "source": np.array([], dtype=object)}


def _hits_extra(T, bx, obstacles) -> bool:
    C, H, Rb = obstacles
    if len(C) == 0:
        return False
    R, t = T[:3, :3], T[:3, 3]
    for c, h in bx:
        if G.obb_overlap(R @ c + t, h, R, C, H, Rb).any():
            return True
    return False


def sample_grasps_cloud(P: np.ndarray, N: np.ndarray, grip: str, approach: str, rot_bin: int, support_z: float,
                        f_dir, extra_obstacles=None, seed: int = 0, cap: int = 60, rot_win: int = ROT_WIN) -> dict:
    """Live candidates on an observed cloud, restricted to the commanded approach family and rot bin +-1 (spec
    step 4): the swept gripper (fingers at the pre-shape opening + palm, back to the stand-off) must clear every
    OTHER cropped point (the object's own far side / neighbouring clutter inside the crop) and `extra_obstacles`
    ((C, H, R) scene cuboids in grasp9.obb_overlap's convention, already in P's frame -- neighbour objects /
    furniture the swept gripper must also clear, step 5's collision check). support_z: the local support plane
    (table / shelf top) the fingertips must stay SUPPORT_CLEAR above. f_dir: base-frame horizontal direction from
    the robot to the object (splits front / side, as grasp9.family)."""
    gr = G.gripper(grip)
    pr = antipodal_pairs_cloud(P, N, gr, seed=seed)
    if not len(pr["w"]):
        return _empty_grasps(gr)
    cos_c = math.cos(math.atan(G.MU))
    phis = np.radians(np.arange(0.0, 360.0, G.STEP_DEG))
    rng = np.random.default_rng(seed + 7)
    T_l, c1, c2, w_l, a_l, pre, sc = [], [], [], [], [], [], []
    for p, q, w, ang in zip(pr["p"], pr["q"], pr["w"], pr["ang"]):
        c = (q - p) / w
        m = (p + q) / 2
        u = np.cross(c, [0.0, 0.0, 1.0])
        if np.linalg.norm(u) < 1e-6:
            u = np.cross(c, [1.0, 0.0, 0.0])
        u = u / np.linalg.norm(u)
        v = np.cross(c, u)
        A = np.cos(phis)[:, None] * u + np.sin(phis)[:, None] * v
        fam = np.array([G.family(a, f_dir) for a in A])
        rb = np.array([G.rot_base(a, c)[1] for a in A])
        d = np.minimum((rb - rot_bin) % 12, (rot_bin - rb) % 12)
        keep = (fam == approach) & (d <= rot_win) & (A[:, 2] <= G.BELOW_Z)
        if not keep.any():
            continue
        open_w = float(min(w + rng.uniform(*G.PRE_OPEN), gr["max_open"]))
        bx_low = G.boxes(gr, open_w)
        bx = G.boxes(gr, max(open_w, w + 0.002), G.STANDOFF)
        cone = min(1 - (1 - math.cos(ang[0])) / (1 - cos_c), 1 - (1 - math.cos(ang[1])) / (1 - cos_c))
        for a in A[keep]:
            R = G.frame_of(a, c)
            T = np.eye(4)
            T[:3, :3], T[:3, 3] = R, m
            if G._lowest(T, bx_low) < support_z + G.SUPPORT_CLEAR:
                continue
            rel = P - m
            if G.hits_boxes(rel @ R, bx):
                continue
            if extra_obstacles is not None and _hits_extra(T, bx, extra_obstacles):
                continue
            T_l.append(T)
            c1.append(p)
            c2.append(q)
            w_l.append(w)
            a_l.append(a)
            pre.append(open_w)
            sc.append(max(cone, 0.0))
    K = len(T_l)
    out = {"T": np.asarray(T_l).reshape(K, 4, 4), "c1": np.asarray(c1).reshape(K, 3),
           "c2": np.asarray(c2).reshape(K, 3), "w": np.asarray(w_l), "a": np.asarray(a_l).reshape(K, 3),
           "score": np.asarray(sc), "pre_open": np.asarray(pre), "gripper": gr,
           "source": np.array(["live_cloud"] * K)}
    return G.thin(out, cap, seed) if K > cap else out


# ---------------------------------------------------------------------------------------------- refiner hook
_REFINER = None


def set_refiner(fn) -> None:
    """Install a learned local refiner: fn(cloud, point3d, approach, rot, gripper) -> candidates dict (the
    sample_grasps_cloud return shape) | None. None / an empty result falls back to the antipodal search in this
    module. Intended for GraspGen-X (licence cleared 2026-10-02: Apache-2.0 code, NVIDIA Open Model License
    weights, internal use) -- NOT wired up by this module; a later task calls set_refiner with the real wrapper."""
    global _REFINER
    _REFINER = fn


def get_refiner():
    return _REFINER


def refine(cloud: np.ndarray, point3d, approach: str, rot: int, gripper: str):
    """The hook point itself: calls the installed refiner if any, else None (-> caller uses the antipodal search).
    Kept as a free function (not a method) so a refiner can be installed from anywhere (tests, a job script) without
    importing rtlive9's Isaac-dependent Runtime."""
    fn = _REFINER
    return None if fn is None else fn(cloud, point3d, approach, rot, gripper)


# ---------------------------------------------------------------------------------------------- choosing
def pick_live(C: dict, point3d) -> int | None:
    """Index of the best live candidate: contact midpoint closest to the commanded point (spec: refine NEAR that
    point), ties broken by the antipodal cone score."""
    if not len(C["w"]):
        return None
    m = (C["c1"] + C["c2"]) / 2
    d = np.linalg.norm(m - np.asarray(point3d, float), axis=1)
    key = sorted(range(len(d)), key=lambda i: (round(float(d[i]) / 0.005), -float(C["score"][i]), i))
    return int(key[0])


def choose_live(P: np.ndarray, N: np.ndarray, grip: str, approach: str, rot_bin: int, point3d, support_z: float,
                f_dir, category: str = "", obj_h: float = 0.0, extra_obstacles=None, seed: int = 0, k: int = 0,
                use_refiner: bool = True, rot_win: int = ROT_WIN):
    """-> v2plan.GraspChoice | None, built on the OBSERVED cloud alone (no per-object cache lookup anywhere in this
    call -- no disk read at all). Tries the installed refiner first (GraspGen-X hook, see `refine`); candidates it returns are
    treated exactly like the antipodal search's (same dict shape) and picked the same way. use_refiner=False
    (tests, A/B 'antipodal only' runs) skips straight to the antipodal search."""
    from . import v2plan as VP
    gr = G.gripper(grip)
    C = None
    if use_refiner:
        C = refine(P, point3d, approach, rot_bin, grip)
    if not C or not len(C.get("w", [])):
        C = sample_grasps_cloud(P, N, grip, approach, rot_bin, support_z, f_dir, extra_obstacles=extra_obstacles,
                                seed=seed, rot_win=rot_win)
    i = pick_live(C, point3d)
    if i is None:
        return None
    d = VP.draws(seed, k)
    T, w, a = C["T"][i], float(C["w"][i]), C["a"][i]
    rb, rdeg = G.rot_base(a, (C["c2"][i] - C["c1"][i]) / max(w, 1e-9))[::-1]
    meta = {"label_rule": "live_v1", "rule_step": 4, "approach_reason": "live_vlm_command", "part": None,
            "category": category, "instructed_approach": approach, "family": approach,
            "rot_deg_base": round(rdeg, 2), "rot_bin_base": int(rb), "rot_bin_img": int(rot_bin),
            "point": [round(float(v), 1) for v in point3d] if np.ndim(point3d) and len(point3d) == 2 else None,
            "point_src": "live_vlm", "point_px_visible": True,
            "grasp_world": np.round(T, 5).tolist(), "contacts_world": [np.round(C["c1"][i], 5).tolist(),
                                                                       np.round(C["c2"][i], 5).tolist()],
            "width_m": round(w, 4), "pre_open_m": round(float(C["pre_open"][i]), 4),
            "approach_vec": np.round(a, 4).tolist(), "score": round(float(C["score"][i]), 4),
            "source": str(C["source"][i]), "obj_h": round(float(obj_h), 4),
            "draws": {x: round(v, 4) if isinstance(v, float) else v for x, v in d.items()},
            "n_live_candidates": int(len(C["w"])), "cloud_n": int(len(P))}
    return VP.GraspChoice(idx=int(i), T=T.copy(), c1=C["c1"][i].copy(), c2=C["c2"][i].copy(), w=w,
                          pre_open=float(C["pre_open"][i]), a=a.copy(), family=str(approach), standoff=d["standoff"],
                          place_dz=d["place_dz"], retreat=d["retreat"], lift_dz=d["lift_dz"], rule_step=4,
                          approach_reason="live_vlm_command", instructed=approach, meta=meta)
