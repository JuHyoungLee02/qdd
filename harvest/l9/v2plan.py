"""L9 v2 truth plan with real grasps (spec §12.4-12.8; research grasp_point_learning_2026-10-02 §11.6-11.9). Pure.

Per episode step (one pick of one target) the generator builds a GraspChoice from the cached candidates of the
target (grasp9 / tools/l9/grasp_test.py) moved to the object's pose:
  valid   = Isaac lift + shake passed (cache) & fingertips above the support & cuRobo IK reach (ik_ok)
  label   = grasp9.select_label (deterministic_v1): top-centre -> scene-constraint family -> robot side / handle /
            reach margin; instructed rows (~20 %) name the family in the instruction
The truth plan is xlabels.plan with these changes:
  above_target  -> the pre-grasp pose: grasp TCP - a * standoff (standoff drawn 8-14 cm), the grasp orientation
  descend_close -> the grasp TCP + orientation, close (the executor runs the straight approach with the pre-shape)
  carry / place -> the held orientation; the put TCP = place pose of the object (x) the grip offset measured at lift;
                   place height + U[0.4, 2] cm (place_dz)
  retreat       -> back along -a (6-12 cm) and up
Commands are the astra-solo@v2 eef commands (position_m, gripper) plus `quat_wxyz` (the executor's orientation);
the point-format label (pt) gets `approach` and `rot` (12 bins of the closing-axis angle in the head image)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import grasp9 as G

STANDOFF = (0.08, 0.14)
PLACE_DZ = (0.004, 0.02)
RETREAT = (0.06, 0.12)
LIFT_DZ = (0.02, 0.05)
INSTRUCTED_P = 0.20
INSTRUCT_TEXT = {"top": "from above", "oblique": "at an angle", "front": "from the front", "side": "from the side"}
VIS_TOL = 0.012  # contact visible when the head depth at its pixel is within 1.2 cm of its camera depth
EDGE_PX = 2


@dataclass
class GraspChoice:
    idx: int
    T: np.ndarray  # world 4x4 of the TCP frame G at the grasp
    c1: np.ndarray
    c2: np.ndarray
    w: float
    pre_open: float
    a: np.ndarray
    family: str
    standoff: float
    place_dz: float
    retreat: float
    lift_dz: float
    rule_step: int
    approach_reason: str
    instructed: str | None
    meta: dict = field(default_factory=dict)

    @property
    def pos(self) -> np.ndarray:
        return self.T[:3, 3]

    @property
    def quat(self) -> np.ndarray:
        return G.mat_quat(self.T[:3, :3])

    @property
    def pre(self) -> np.ndarray:
        return self.pos - self.a * self.standoff


def draws(seed: int, k: int) -> dict:
    """Per-episode, per-pick continuous draws (standoff, place height, retreat, lift) and the instructed coin."""
    r = np.random.default_rng([int(seed), 912, int(k)])
    return {"standoff": float(r.uniform(*STANDOFF)), "place_dz": float(r.uniform(*PLACE_DZ)),
            "retreat": float(r.uniform(*RETREAT)), "lift_dz": float(r.uniform(*LIFT_DZ)),
            "instructed": bool(r.random() < INSTRUCTED_P), "alt": int(r.integers(1 << 30))}


def visible(cam, depth, p, tol: float = VIS_TOL) -> tuple:
    """(visible, near_edge, pixel) of world point p in the head camera with its z-depth image."""
    from ..astra_motion.geometry import project
    u, v, z = project(cam, p)
    if not (z > 0 and math.isfinite(u)) or not (0 <= u < cam.W and 0 <= v < cam.H):
        return False, False, None
    iu, iv = int(u), int(v)
    if depth is None:
        return True, False, (u, v)
    d = float(depth[iv, iu])
    ok = math.isfinite(d) and abs(d - z) <= tol
    win = depth[max(iv - EDGE_PX, 0):iv + EDGE_PX + 1, max(iu - EDGE_PX, 0):iu + EDGE_PX + 1]
    edge = bool(np.nanmax(win) - np.nanmin(win) > 0.03) if win.size else False
    return ok, edge, (u, v)


def label_point(cam, depth, c1, c2) -> dict:
    """Point label = the grasp centre's projection when visible, else the visible contact nearer the camera
    (research §11.6 risk 2). Records both contacts' pixels and visibility."""
    from ..astra_motion.geometry import project
    from ..astra_solo.resolve import to_scaled
    m = (np.asarray(c1) + np.asarray(c2)) / 2
    vm, em, pm = visible(cam, depth, m, tol=0.06)  # the centre lies inside the object: generous depth tolerance
    v1, e1, p1 = visible(cam, depth, c1)
    v2, e2, p2 = visible(cam, depth, c2)
    sc = lambda p: None if p is None else to_scaled(p[0], p[1], cam.W, cam.H)
    if pm is not None and (vm or v1 or v2):
        pt, src, edge = pm, "centre", em
    elif v1 or v2:
        z1, z2 = project(cam, c1)[2], project(cam, c2)[2]
        use1 = v1 and (not v2 or z1 <= z2)
        pt, src, edge = (p1, "contact1", e1) if use1 else (p2, "contact2", e2)
    else:
        pt, src, edge = pm, "hidden", em
    return {"point": sc(pt), "point_src": src, "point_px_visible": src != "hidden" and pt is not None,
            "grasp_center_px": sc(pm), "contact_px_head": [sc(p1), sc(p2)], "contact_visible": [bool(v1), bool(v2)],
            "point_depth_edge": bool(edge)}


def choose(C_world: dict, ok: np.ndarray, margin: np.ndarray, obj_centre, robot_xy, seed: int, k: int,
           constraint: str | None = None, cam=None, depth=None, allow_instruct: bool = True):
    """-> GraspChoice | None for one pick (k = step index). C_world = grasp9.to_world(...) of the cached candidates;
    ok / margin per candidate (validity incl. reach; reach margin)."""
    d = draws(seed, k)
    a = C_world["a"]
    m = (C_world["c1"] + C_world["c2"]) / 2
    cx = np.asarray(obj_centre, float)
    f_dir = cx[:2] - np.asarray(robot_xy, float)[:2]
    fam = np.array([G.family(v, f_dir) for v in a])
    centre_d = np.hypot(m[:, 0] - cx[0], m[:, 1] - cx[1])
    robot_d = np.hypot(m[:, 0] - robot_xy[0], m[:, 1] - robot_xy[1])
    instructed = None
    fams_ok = sorted({f for f, o in zip(fam, ok) if o})
    if allow_instruct and d["instructed"] and len(fams_ok) > 1:
        pref = [f for f in ("side", "front", "oblique", "top") if f in fams_ok]
        instructed = pref[d["alt"] % len(pref)]
    i, step, why = G.select_label(fam, centre_d, robot_d, margin, ok, constraint=constraint, instructed=instructed)
    if i is None:
        return None
    T = C_world["T"][i]
    meta = {"label_rule": "deterministic_v1", "rule_step": step, "approach_reason": why,
            "instructed_approach": instructed, "family": str(fam[i]),
            "ik_ok_by_family": {f: bool(((fam == f) & ok).any()) for f in G.FAMILIES},
            "n_valid_by_family": {f: int(((fam == f) & ok).sum()) for f in G.FAMILIES},
            "random_alt_idx": int(np.flatnonzero(ok)[d["alt"] % int(ok.sum())]),
            "grasp_world": np.round(T, 5).tolist(), "contacts_world": [np.round(C_world["c1"][i], 5).tolist(),
                                                                       np.round(C_world["c2"][i], 5).tolist()],
            "width_m": round(float(C_world["w"][i]), 4), "pre_open_m": round(float(C_world["pre_open"][i]), 4),
            "approach_vec": np.round(a[i], 4).tolist(), "score": round(float(C_world["score"][i]), 4),
            "source": str(C_world["source"][i]), "draws": {x: round(v, 4) if isinstance(v, float) else v
                                                         for x, v in d.items()}}
    rb, rdeg = G.rot_base(a[i], (C_world["c2"][i] - C_world["c1"][i]) / max(C_world["w"][i], 1e-9))[::-1]
    meta.update(rot_deg_base=round(rdeg, 2), rot_bin_base=int(rb))
    open_cm = round(float(C_world["pre_open"][i]) * 100)
    w = float(C_world["w"][i])
    meta.update(open_cm_bin=int(open_cm), open_bin3="narrow" if w < 0.03 else ("mid" if w < 0.06 else "wide"))
    if cam is not None:
        c = (C_world["c2"][i] - C_world["c1"][i]) / max(w, 1e-9)
        K = np.array([[cam.fx, 0, cam.cx], [0, cam.fy, cam.cy], [0, 0, 1.0]])
        deg, b = G.rot_img(m[i], c, K, np.asarray(cam.R, float), np.asarray(cam.t, float))
        meta.update(rot_deg_img=round(deg, 2), rot_bin_img=int(b))
        meta.update(label_point(cam, depth, C_world["c1"][i], C_world["c2"][i]))
        vs = []
        for j in np.flatnonzero(ok)[:64]:
            cj = (C_world["c2"][j] - C_world["c1"][j]) / max(C_world["w"][j], 1e-9)
            _, bj = G.rot_img(m[j], cj, K, np.asarray(cam.R, float), np.asarray(cam.t, float))
            lp = label_point(cam, depth, C_world["c1"][j], C_world["c2"][j])
            vs.append({"family": str(fam[j]), "rot_bin_img": int(bj), "point": lp["point"],
                       "visible": lp["point_px_visible"], "T": np.round(C_world["T"][j], 4).tolist()})
        meta["valid_set"] = vs
    return GraspChoice(idx=int(i), T=T.copy(), c1=C_world["c1"][i].copy(), c2=C_world["c2"][i].copy(), w=w,
                       pre_open=float(C_world["pre_open"][i]), a=a[i].copy(), family=str(fam[i]),
                       standoff=d["standoff"], place_dz=d["place_dz"], retreat=d["retreat"], lift_dz=d["lift_dz"],
                       rule_step=step, approach_reason=why, instructed=instructed, meta=meta)


def instruction_suffix(gc: GraspChoice | None) -> str:
    return "" if gc is None or gc.instructed is None else f" Grasp it {INSTRUCT_TEXT[gc.instructed]}."


def _r(p) -> list:
    return [round(float(v), 4) for v in p]


def _q(q) -> list:
    return [round(float(v), 5) for v in q]


NEAR_POS, NEAR_DEG = 0.015, 12.0


def ang_deg(q1, q2) -> float:
    d = abs(float(np.dot(np.asarray(q1, float), np.asarray(q2, float))))
    return math.degrees(2 * math.acos(min(1.0, d)))


def plan(st: dict, info: dict, table_z: float, w_open: float, gc: GraspChoice, held: dict | None):
    """-> (step, command | None). st: world.status() with 'tcp' and 'tcp_quat'; held: {'T_obj_G'} measured after the
    close (None before). The steps keep the xlabels names (labels / texts / phase stay comparable)."""
    from ..teach_l8d import xlabels as XL
    from ..teach_l8 import labels as L
    from ..astra_motion.harness import obj_height
    tg, pl = info["tgt"], info["place"]
    pred = st["pred"]
    tcp = np.asarray(st["tcp"], float)
    tq = np.asarray(st.get("tcp_quat", gc.quat), float)
    hold = pred.get(f"holding({tg})") is True
    H = XL.heights(info, table_z)
    h = obj_height(tg)
    p = np.asarray(st["obj"][pl], float)
    if info.get("place_xy_offset"):
        p = p + np.array([*info["place_xy_offset"], 0.0], float)
    c = np.asarray(st["obj"][tg], float)
    if pred.get(f"on({tg},{pl})") is True and not hold:
        away = tcp - gc.a * gc.retreat
        if float(np.linalg.norm(tcp[:2] - c[:2])) < L.RETREAT_XY + 0.03 and tcp[2] < c[2] + h / 2 + L.RETREAT_ABOVE:
            tgt = np.array([away[0], away[1], max(away[2], tcp[2]) + 0.04])
            return "retreat", {"mode": "eef", "position_m": _r(tgt), "gripper": "keep", "quat_wxyz": _q(tq)}
        return "done", {"mode": "stop"}
    if not hold and pred.get(f"upright({tg})") is False:
        return "tipped", None
    zc = H["carry_base"] + L.CARRY_DZ
    if hold:
        T_og = held["T_obj_G"] if held else None
        if T_og is not None:  # put TCP: object upright at the place (its current yaw), bottom place_dz above the top
            T_w_obj = np.eye(4)
            T_w_obj[:3, :3] = G.qmat(st["obj_quat"][tg])
            T_w_obj[:3, 3] = [p[0], p[1], H["place_top"] + h / 2 + gc.place_dz]
            put_T = T_w_obj @ T_og
            put, pq = put_T[:3, 3], G.mat_quat(put_T[:3, :3])
        else:
            put, pq = np.array([p[0], p[1], H["place_top"] + (tcp[2] - (c[2] - h / 2)) + gc.place_dz]), tq
        if np.linalg.norm(tcp[:2] - put[:2]) < L.NEAR_XY:
            return "lower_open", {"mode": "eef", "position_m": _r(put), "gripper": "open", "quat_wxyz": _q(pq)}
        if tcp[2] >= zc - L.NEAR_XY:
            return "carry_over", {"mode": "eef", "position_m": _r([put[0], put[1], max(zc, put[2] + 0.05)]),
                                  "gripper": "keep", "quat_wxyz": _q(pq)}
        return "carry_up", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], zc]), "gripper": "keep",
                            "quat_wxyz": _q(tq)}
    if float(st["grip_w"]) < min(w_open, gc.pre_open) - 2 * L.OPEN_TOL:  # the pre-shape is narrower than w_open
        return "reopen", {"mode": "gripper", "gripper": "open"}
    pre = gc.pre
    if np.linalg.norm(tcp - pre) < NEAR_POS + 0.01 and ang_deg(tq, gc.quat) < NEAR_DEG or \
            np.linalg.norm(tcp - gc.pos) < gc.standoff * 0.9 and ang_deg(tq, gc.quat) < NEAR_DEG:
        return "descend_close", {"mode": "eef", "position_m": _r(gc.pos), "gripper": "close", "quat_wxyz": _q(gc.quat)}
    low = H["sup_tgt"] + h + L.LOW_MARGIN
    if tcp[2] < low and np.linalg.norm(tcp[:2] - c[:2]) > 0.06:
        return "lift_clear", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], low + 0.05]), "gripper": "keep",
                              "quat_wxyz": _q(tq)}
    return "above_target", {"mode": "eef", "position_m": _r(pre), "gripper": "keep", "quat_wxyz": _q(gc.quat)}
