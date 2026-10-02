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
import os
from dataclasses import dataclass, field

import numpy as np

from . import grasp9 as G

SEL = os.environ.get("L9V2_SEL", "natural_v1")  # label rule: natural_v1 (spec) | ggx_v1 (GraspGenX + sim, opt-in)

# place_oscillation fix (docs/research/place_oscillation_2026-10-03.md §4, owner order 10-03 04h): above<->lift
# ("들었다 놨다") came from a height-only carry_over/carry_up split plus a TCP/put xy gate wide enough to mask
# tracking sag (NEAR_PUT below) but not tied to the held object's own position. Both opt-in (env flags), each
# additive and off by default -- today's byte-identical control flow is the K0 arm of the 8B check ladder.
PLACE_TOL_FIX = os.environ.get("L9V2_PLACE_TOL", "0") == "1"  # (a) tolerance-based lower_open, held-object centre
PLACE_HYST_FIX = os.environ.get("L9V2_PLACE_HYST", "0") == "1"  # (d) hysteresis: no carry_up once committed
PLACE_SUCCESS_TOL = 0.03  # m, task success xy allowance (bimanual9.success_a/b/d's own default) -- tol_rel's basis
PLACE_TOL_MAX = 0.025  # m, doc §4 (a): tol_rel capped around the large-place pointing allowance
PLACE_ABOVE_FIX = os.environ.get("L9V2_PLACE_ABOVE", "0") == "1"  # P0: carry_over physically targets the height
# "above" actually executes at (resolve.py), not the 22 cm carry height (doc §0.3). Heavier / riskier than (a)/(d)
# -- new rows only, needs a pod collision/IK smoke batch before any A/B or production use (owner order 10-03 04h,
# coordinator a8f68de3d815957c2: "서두르다 깨진 코드를 올리지 말고").
PLACE_ABOVE_DZ = 0.08  # m = astra_solo.resolve.ABOVE_DZ, duplicated as a literal (v2plan must not import resolve,
# which needs camera/runtime state v2plan doesn't have): test_v2plan.test_place_above_dz_matches_resolve pins them.

STANDOFF = (0.08, 0.14)
PLACE_DZ = (0.008, 0.025)  # pilot 10-02: placing 4 mm above the surface pushed the object into it (wrist jolts)
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
           constraint: str | None = None, cam=None, depth=None, allow_instruct: bool = True, parts=None,
           category: str = "", height: float = 0.0):
    """-> GraspChoice | None for one pick (k = step index). C_world = grasp9.to_world(...) of the cached candidates;
    ok / margin per candidate (validity incl. reach; reach margin). With `parts` (per-candidate grasped part) the
    natural rule (natural_v1: the object kind's natural (family, part) order, spec §12.8 rev. 10-02 03h) picks the
    label; without it the older deterministic_v1 rule (tests / fallbacks)."""
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
    order = G.natural_order(category, height, constraint) if parts is not None else None
    if allow_instruct and d["instructed"] and len(fams_ok) > 1:
        first = order[0][0] if order else None
        pref = [f for f in ("side", "front", "oblique", "top") if f in fams_ok and f != first]
        instructed = pref[d["alt"] % len(pref)] if pref else None
    rank = None
    S = None
    if parts is not None and SEL == "ggx_v1" and "ggx_s" in C_world:
        i, step, rank, S = G.select_ggx(fam, parts, robot_d, margin, ok, order, C_world["ggx_s"],
                                        C_world.get("slip_mm", np.full(len(ok), np.nan)), instructed=instructed)
        why = "instructed" if instructed else (f"scene_constraint:{constraint}" if constraint else "natural")
        rule = "ggx_v1"
    elif parts is not None:
        i, step, rank = G.select_natural(fam, parts, robot_d, margin, ok, order, instructed=instructed)
        why = "instructed" if instructed else (f"scene_constraint:{constraint}" if constraint else "natural")
        rule = "natural_v1"
    else:
        i, step, why = G.select_label(fam, centre_d, robot_d, margin, ok, constraint=constraint, instructed=instructed)
        rule = "deterministic_v1"
    if i is None:
        return None
    T = C_world["T"][i]
    meta = {"label_rule": rule, "rule_step": step, "approach_reason": why, "natural_rank": rank,
            "natural_order": [list(x) for x in order] if order else None,
            "part": None if parts is None else str(parts[i]), "category": category,
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
    if S is not None:
        sl = float(C_world.get("slip_mm", np.full(len(ok), np.nan))[i])
        meta.update(sel_score=round(float(S[i]), 4), ggx_score=round(float(C_world["ggx_s"][i]), 4),
                    slip_mm=None if not np.isfinite(sl) else round(sl, 2))
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
NEAR_PUT = 0.03


def ang_deg(q1, q2) -> float:
    d = abs(float(np.dot(np.asarray(q1, float), np.asarray(q2, float))))
    return math.degrees(2 * math.acos(min(1.0, d)))


def _in_frame(cam, p, margin: float = 0.05) -> bool:
    """True if world point p projects inside the head image with a `margin` inset fraction of each side (same
    convention as world9._head_sees)."""
    from ..astra_motion.geometry import project
    u, v, z = project(cam, p)
    return bool(z > 0 and math.isfinite(u) and math.isfinite(v) and
                margin * cam.W <= u <= (1 - margin) * cam.W and margin * cam.H <= v <= (1 - margin) * cam.H)


def inview_score(cam, pts, margin: float = 0.05) -> float:
    """Fraction of world points (e.g. TCP, held-object centre) inside the head image with `margin` (0.0 if cam is
    None or pts is empty)."""
    if cam is None or not pts:
        return 0.0
    return sum(1 for p in pts if _in_frame(cam, p, margin)) / len(pts)


def carry_over_z(zc: float, put_z_floor: float, put_xy, pq, T_obj_G, cam=None, margin: float = 0.05) -> float:
    """z for the carry_over waypoint (L9_CARRY_INVIEW, soft preference, user order 10-03). The two candidates are
    already computed by the caller -- zc (the carry height) and put_z_floor = put[2] + 0.05 (today's floor) -- no
    new constant and no wider range. With a head camera and the held-object grip transform, pick whichever of the
    two keeps the TCP and the held-object centre inside the head image more often (world9._head_sees's 5% margin
    convention); ties, or no camera / no held transform (flag off), keep today's choice (max(zc, put_z_floor))."""
    default = max(float(zc), float(put_z_floor))
    other = min(float(zc), float(put_z_floor))
    if cam is None or T_obj_G is None or default == other:
        return default

    def score(z: float) -> float:
        T = np.eye(4)
        T[:3, :3] = G.qmat(pq)
        T[:3, 3] = [put_xy[0], put_xy[1], z]
        obj_p = (T @ np.asarray(T_obj_G, float))[:3, 3]
        return inview_score(cam, [T[:3, 3], obj_p], margin)

    return other if score(other) > score(default) else default


def put_pose(obj_quat_held, place_xy, centre_z: float, T_obj_G, yaw_delta: float = 0.0) -> np.ndarray:
    """TCP pose that puts the held object down UPRIGHT (its held yaw + yaw_delta) with its centre at
    (place_xy, centre_z); the hand keeps the grip measured at the lift (T_obj_G). Pilot 10-02: placing with the held
    tilt tipped objects over."""
    Rh = G.qmat(obj_quat_held)
    yaw = math.atan2(Rh[1, 0], Rh[0, 0]) + float(yaw_delta)
    T_w_obj = np.eye(4)
    T_w_obj[:3, :3] = G.qmat(G.yaw_quat(yaw))
    T_w_obj[:3, 3] = [place_xy[0], place_xy[1], centre_z]
    return T_w_obj @ np.asarray(T_obj_G, float)


def place_tol(key: str) -> float:
    """xy allowance (m) for 'close enough to place regardless of height' (fix (a)): half the task success
    tolerance, floored at this place object's own pointing resolution (astra_solo.pt_truth.xy_tol: 12 mm small
    objects / 25 mm a large tray) and capped at PLACE_TOL_MAX. L9V2_PLACE_TOL only."""
    from ..astra_solo.pt_truth import xy_tol
    return min(max(0.5 * PLACE_SUCCESS_TOL, xy_tol(key)), PLACE_TOL_MAX)


def carry_z(H: dict, carry_dz: float, gc, tcp, c, h: float, hold: bool) -> float:
    """TCP carry height. Default: carry_base + CARRY_DZ (0.22). A robot with a short vertical reach (R1 Pro, L9v2-R1:
    its leaned arm reaches only ~0.2-0.3 m of height at a given distance) sets gc.carry_clear (a per-episode draw from
    a range): the held object's bottom clears carry_base by that much, i.e. TCP = carry_base + (TCP - object bottom)
    + carry_clear, never above the default."""
    clear = getattr(gc, "carry_clear", None)
    zd = H["carry_base"] + carry_dz
    if clear is None or not hold:
        return zd if clear is None else min(zd, H["carry_base"] + h + float(clear) + 0.03)
    hang = float(tcp[2]) - (float(c[2]) - h / 2)
    return min(zd, H["carry_base"] + max(hang, 0.0) + float(clear))


def plan(st: dict, info: dict, table_z: float, w_open: float, gc: GraspChoice, held: dict | None, cam=None):
    """-> (step, command | None). st: world.status() with 'tcp' and 'tcp_quat'; held: {'T_obj_G'} measured after the
    close (None before). The steps keep the xlabels names (labels / texts / phase stay comparable). cam: head
    camera for L9_CARRY_INVIEW (None = unchanged carry_over height, the default)."""
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
    zc = carry_z(H, L.CARRY_DZ, gc, tcp, c, h, hold)
    if hold:
        T_og = held["T_obj_G"] if held else None
        if PLACE_ABOVE_FIX and held is not None and "grip_offset" not in held:
            # P0 (docs/research/place_oscillation_2026-10-03.md §0.3): captured once, right after the close, the
            # same way astra_solo.resolve.py's executor measures it ("TCP height above the plane when the gripper
            # last closed") -- so carry_over's target below matches what "above" actually executes as.
            held["grip_offset"] = float(tcp[2]) - float(H["sup_tgt"])
        if T_og is not None:  # put TCP: object upright at the place (its current yaw), bottom place_dz above the top
            put_T = put_pose(st["obj_quat"][tg], p, H["place_top"] + h / 2 + gc.place_dz, T_og,
                             float((held or {}).get("yaw_delta", 0.0)))
            put, pq = put_T[:3, 3], G.mat_quat(put_T[:3, :3])
        else:
            put, pq = np.array([p[0], p[1], H["place_top"] + (tcp[2] - (c[2] - h / 2)) + gc.place_dz]), tq
        if PLACE_TOL_FIX:  # (a): the HELD OBJECT's own centre vs the place, not TCP/put (sag-proof); no lift once
            obj_near = float(np.linalg.norm(c[:2] - p[:2]))  # the object is close enough to place, at any height
            tol = place_tol(pl)
            near = obj_near < tol
        else:
            near = float(np.linalg.norm(tcp[:2] - put[:2])) < NEAR_PUT  # carrying sags / lags 1-3 cm (looped)
            obj_near, tol = None, NEAR_PUT
        committed = False
        if PLACE_HYST_FIX:  # (d): once the carry has brought the object within 2x tol, don't relabel it lift
            if held is not None:  # (no observed failure -- a drop/slip ends the hold, which resets `held` upstream)
                held["carry_committed"] = bool(held.get("carry_committed")) or (
                    obj_near if obj_near is not None else float(np.linalg.norm(c[:2] - p[:2]))) < 2 * tol
            committed = bool(held and held.get("carry_committed"))
            # smoke 10-03 (kit_to_sink): carry_over<->lower_open at the tol edge -- once lowering started, stay with
            # it while the object is within 1.5x tol (place side; 2x tol = the success tolerance itself, so the band
            # stays inside it with margin -- releasing at the success edge would trade the loop for off-centre places)
            if obj_near is not None and held is not None:
                if held.get("lowering") and obj_near < 1.5 * tol:
                    near = True
                if near:
                    held["lowering"] = True
        lifted = False
        if PLACE_ABOVE_FIX and held is not None:
            # smoke 10-03 (sel_bigger): P0's carry_over goes BELOW zc - NEAR_XY, so the height test alone flipped the
            # next call back to carry_up. Latch "reached carry height once" per hold; lift-first is kept.
            if tcp[2] >= zc - L.NEAR_XY:
                held["p0_lifted"] = True
            lifted = bool(held.get("p0_lifted"))
        if near:
            return "lower_open", {"mode": "eef", "position_m": _r(put), "gripper": "open", "quat_wxyz": _q(pq)}
        if committed or lifted or tcp[2] >= zc - L.NEAR_XY:
            if PLACE_ABOVE_FIX:
                # P0: physically roll out "above" at the height it actually executes at (resolve.py's own
                # convention: place top + ABOVE_DZ + grip_offset), not the 22 cm carry height -- the fix for the
                # above(8cm label)<->lift(22cm trajectory) covariate shift. carry_up (lift) is unchanged.
                go = held.get("grip_offset") if held else None
                go = go if go is not None else float(tcp[2] - (c[2] - h / 2))  # defensive fallback, never crashes
                z_over = H["place_top"] + PLACE_ABOVE_DZ + go
            else:
                z_over = carry_over_z(zc, put[2] + 0.05, put[:2], pq, T_og, cam=cam)
            return "carry_over", {"mode": "eef", "position_m": _r([put[0], put[1], z_over]),
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
