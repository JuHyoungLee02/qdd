"""L9 generic hand / gripper layer (user order 10-03 03시, L9_PRINCIPLES "집게·손 공통 층"). Pure numpy, no Isaac.

One model for every gripper, current and future: a parallel 2-finger gripper is the N = 2 case of an N-finger hand.

  hand descriptor (the ONLY hand-authored input, assets9/grippers/hands9.json): the fingertip links + which tips
      oppose which (thumb vs the rest, or a pair). Everything else is derived by tools/onboard/hand_sweep.py from
      the gripper URDF's collision meshes by FK while sweeping the closing path:
  gap table (assets9/grippers/gap9/<gripper>.json): per closing-path row the finger joints and the MEASURED free
      gap between the opposing finger chains at the TCP plane of frame G (z_G in BANDS, |x_G| < XH; the G1 lesson:
      pad-point / tip-to-tip tables were 30-45 mm off), plus the fingertip contact points per row and the derived
      grasp frame (convergence point of the fingertip paths, closing axis, palm normal).

Runtime use (opt-in, L9_GRIP_LAYER=1; unset = byte-identical):
  (1) opening <-> finger joints through the gap table (GapTable.joints_for_gap / gap_of_q) for every robot
  (2) pre-grasp opening clipped to the measured max gap; EMPTY/closed judged on the measured gap (close_verdict)
  (3) holding = contact on ANY fingertip / pad + the MAX finger-joint effort (holding), one function for N fingers
  (4) frame + GraspGen-X gripper name per (profile, arm) (frame_check, GGX_GRIPPER)
  (5) scene placement: per-robot reach / camera models plug in through SCENE_MODELS (the R1 / G1 teams' own
      placement code -- g1reach9.G1Reach, r1_band -- registers there; nothing is re-implemented here)
  (6) torso: torso_check -- one posture per episode (random within the robot's range between episodes, never
      moved during an episode)."""
from __future__ import annotations

import json
import math
import os

import numpy as np

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9", "grippers")
GAP_DIR = os.path.join(DIR, "gap9")
# free-gap window in frame G (z_G = -approach): two slices from 20 mm ahead of the TCP plane to 10 mm behind it,
# |x_G| < 20 mm (G1 owner 10-02, g1_free_gap.py -- validated on the Dex3-1, reused for every gripper)
BANDS = ((-0.020, -0.005), (-0.005, 0.010))
XH = 0.020
TCP_BAND = ((-0.005, 0.005),)  # the TCP plane itself (+-5 mm): the contact-width reading
CLOSED_TOL = 0.002  # rows with a free gap <= 2 mm are "closed" (collapse into one closed row at gap 0)
EMPTY_TOL = 0.003  # settled measured gap <= closed + 3 mm: nothing between the fingers (= rt9.EMPTY_M)
CONTACT_TOL, CONTACT_TOL_HI = 0.008, 0.020  # = rt9 (settled gaps run ~1.5 cm over the contact width)
FORCE_MIN_N = 0.5  # = harvest.sim.oracle_state CONTACT_FORCE_N order of magnitude (finger contact)
EFFORT_MIN = 1.0  # = harvest.predicates GRIP_EFFORT_MIN
OPEN_TOL = 0.005  # "open" = measured gap within 5 mm of the measured max
PRE_CLEAR = 0.020  # pre-open >= contact width + 2 cm of REAL free gap (1 cm each side; g1b H5, every robot)

# profile + arm -> gripper json name (assets9/grippers/<name>.json, its gap9 table, its GraspGen-X registration)
GRIPPER_JSON = {("ffw_sg2", "right"): "ffw_sg2_right", ("ffw_sg2", "left"): "ffw_sg2_left",
                ("franka_mast", "right"): "franka_hand", ("r1pro", "right"): "r1pro_right",
                ("r1pro", "left"): "r1pro_left", ("g1", "right"): "g1_right", ("g1", "left"): "g1_left"}
# GraspGen-X server registrations (gripper_json/<name>.json on the shared queue's server); g1 = frame-G sweep
GGX_GRIPPER = {"ffw_sg2_right": "ffw_sg2_right", "ffw_sg2_left": "ffw_sg2_left", "r1pro_right": "r1pro_right",
               "r1pro_left": "r1pro_left", "g1_right": "g1_right_tcp", "g1_left": "g1_left_tcp",
               "franka_hand": "franka_hand"}
# (5) per-robot scene placement models: profile -> factory(arm, **kw) returning an object with the reach9
# ReachModel duck type (reach_points / visible_points). Empty here: the robot teams register their own
# (g1reach9.G1Reach under L9V2_G1_REACH, r1_band under the R1 flags); a robot without an entry keeps the default.
SCENE_MODELS: dict = {}


def enabled() -> bool:
    return os.environ.get("L9_GRIP_LAYER") == "1"


def diag() -> bool:
    """L9_GRIP_DIAG=1: record the close truth next to the verdict (A/B counting; no behaviour change)."""
    return os.environ.get("L9_GRIP_DIAG") == "1"


def register_scene_model(profile: str, factory) -> None:
    SCENE_MODELS[profile] = factory


def _import(spec: str):
    import importlib
    mod, name = spec.split(":")
    return getattr(importlib.import_module(mod), name)


def scene_model(profile: str, default=None, **kw):
    """The robot's own reach / camera model for scene placement: a registered factory, else the env profile's
    "scene_model" ("module:factory"), else `default` (the AI Worker ReachModel). Factory contract:
    factory(seed=int, arm=str, profile=dict | None) -> object with the reach9 ReachModel duck type (at_lift / cam)
    or reach_xy(arm, X, Y, top) [+ margin_px] (reach9.reach_points / visible_points dispatch on it)."""
    f = SCENE_MODELS.get(profile)
    if f is None:
        from . import envprof9 as E
        p = E.load(profile)
        if p and p.get("scene_model"):
            f = _import(p["scene_model"])
            kw.setdefault("profile", p)
    return f(**kw) if f is not None else default


# ---------------------------------------------------------------------------------------------- descriptor
def descriptors() -> dict:
    return json.load(open(os.path.join(DIR, "hands9.json"), encoding="utf-8"))["hands"]


def descriptor(name: str) -> dict:
    d = dict(descriptors()[name])
    d["name"] = name
    return d


# ---------------------------------------------------------------------------------------------- geometry (pure)
def to_G(P: np.ndarray, T_base_G: np.ndarray) -> np.ndarray:
    """Points in the gripper base frame -> frame G (T_base_G = pose of G in the base frame)."""
    Ti = np.linalg.inv(np.asarray(T_base_G, float))
    return np.asarray(P, float) @ Ti[:3, :3].T + Ti[:3, 3]


def _band(P, lo, hi, xh):
    return P[(P[:, 2] >= lo) & (P[:, 2] < hi) & (np.abs(P[:, 0]) < xh)]


def opposed_gap(PA: np.ndarray, PB: np.ndarray, bands=BANDS, xh: float = XH) -> float:
    """Free gap (m) along the closing axis y_G between two opposing finger groups (points in frame G): per band of
    z_G, the slot between the inner-most points of the two sides; the smallest over the bands. Negative = overlap,
    nan = the groups never share a band (fully open beyond the window)."""
    PA, PB = np.asarray(PA, float).reshape(-1, 3), np.asarray(PB, float).reshape(-1, 3)
    if not len(PA) or not len(PB):
        return float("nan")
    sgn = np.sign(PB[:, 1].mean() - PA[:, 1].mean()) or 1.0
    gaps = []
    for lo, hi in bands:
        a, b = _band(PA, lo, hi, xh), _band(PB, lo, hi, xh)
        if len(a) and len(b):
            gaps.append(b[:, 1].min() - a[:, 1].max() if sgn > 0 else a[:, 1].min() - b[:, 1].max())
    return float(min(gaps)) if gaps else float("nan")


def hand_gap(groups: dict, opposition, bands=BANDS, xh: float = XH) -> float:
    """groups: tip name -> finger-chain points (frame G); opposition: [[tips A], [tips B]] pairs (list of pairs).
    The binding (smallest) gap over the opposing pairs -- 2-finger and N-finger the same way."""
    out = []
    for A, B in opposition:
        PA = np.concatenate([groups[t] for t in A])
        PB = np.concatenate([groups[t] for t in B])
        g = opposed_gap(PA, PB, bands, xh)
        if np.isfinite(g):
            out.append(g)
    return float(min(out)) if out else float("nan")


def contact_patch(P_tip: np.ndarray, toward: np.ndarray, depth: float = 0.002) -> tuple:
    """A fingertip's contact patch: its points within `depth` of its inner-most extent towards `toward` (the
    opposing side's centroid). -> (patch centroid, (z_min, z_max) of the patch in frame G)."""
    P = np.asarray(P_tip, float)
    d = np.asarray(toward, float) - P.mean(0)
    d = d / max(np.linalg.norm(d), 1e-9)
    s = P @ d
    pa = P[s >= s.max() - depth]
    return pa.mean(0), (float(pa[:, 2].min()), float(pa[:, 2].max()))


def tip_points(tips: dict, opposition) -> dict:
    """tip name -> (contact patch centroid, patch z range) in frame G, for every tip in the opposition pairs."""
    out = {}
    for A, B in opposition:
        cA = np.concatenate([tips[t] for t in A]).mean(0)
        cB = np.concatenate([tips[t] for t in B]).mean(0)
        for t in A:
            out[t] = contact_patch(tips[t], cB)
        for t in B:
            out[t] = contact_patch(tips[t], cA)
    return out


def derived_frame(contacts_closed: dict, contacts_open: dict, opposition, palm_pts: np.ndarray,
                  z_open: list | None = None) -> dict:
    """The grasp frame from the fingertip paths (all inputs in frame G; contacts = tip -> patch centroid):
    tcp = where the fingertip contact patches converge (midpoint of the two sides at the narrowest open row),
    closing = side A -> side B direction of the patches at the open row (unit),
    approach = palm normal: from the nearest palm point to the tcp, orthogonal to closing (unit),
    z_pads = the z_G range covered by the open row's contact patches (the TCP plane must cross it)."""
    A, B = opposition[0]  # midpoint of the two SIDES (not of all tips: a 2-vs-1 hand would bias towards the 2)
    tcp = (np.mean([contacts_closed[t] for t in A], axis=0) + np.mean([contacts_closed[t] for t in B], axis=0)) / 2
    A, B = opposition[0]
    ca = np.mean([contacts_open[t] for t in A], axis=0)
    cb = np.mean([contacts_open[t] for t in B], axis=0)
    closing = (cb - ca) / max(np.linalg.norm(cb - ca), 1e-9)
    P = np.asarray(palm_pts, float)
    near = P[int(np.argmin(np.linalg.norm(P - tcp[None], axis=1)))] if len(P) else np.zeros(3)
    ap = tcp - near
    ap = ap - (ap @ closing) * closing
    approach = ap / max(np.linalg.norm(ap), 1e-9)
    zr = np.asarray(z_open, float).reshape(-1, 2) if z_open else np.zeros((1, 2))
    return {"tcp": tcp, "closing": closing, "approach": approach,
            "z_pads": np.array([zr[:, 0].min(), zr[:, 1].max()])}


def frame_check(fr: dict, lat_tol: float = 0.010, z_margin: float = 0.005, ang_tol_deg: float = 15.0) -> dict:
    """Derived frame (in frame G) vs frame G itself: the closing axis must be +-y_G, the approach (palm normal)
    -z_G, the tcp centred between the fingertips (|x, y| <= lat_tol) and the TCP plane z_G = 0 must cross the
    fingertips' contact patches (within z_margin). Every gripper's own TCP rule (pad centre, pinch point, ...)
    passes this; a swapped / flipped frame or a TCP off the pads does not."""
    def ang(u, v):
        return float(np.degrees(math.acos(float(np.clip(abs(np.dot(u, v)), -1.0, 1.0)))))
    e_cl = ang(np.asarray(fr["closing"], float), np.array([0.0, 1.0, 0.0]))
    a = np.asarray(fr["approach"], float)
    e_ap = float(np.degrees(math.acos(float(np.clip(np.dot(a, [0.0, 0.0, -1.0]), -1.0, 1.0)))))
    t = np.asarray(fr["tcp"], float)
    lat = float(np.linalg.norm(t[:2]))
    zp = np.asarray(fr.get("z_pads", (0.0, 0.0)), float)
    z_ok = bool(zp[0] - z_margin <= 0.0 <= zp[1] + z_margin)
    return {"closing_err_deg": round(e_cl, 2), "approach_err_deg": round(e_ap, 2),
            "tcp_lateral_mm": round(lat * 1e3, 2), "tcp_z_mm": round(float(t[2]) * 1e3, 2),
            "pads_z_mm": [round(float(v) * 1e3, 1) for v in zp], "tcp_plane_on_pads": z_ok,
            "ok": e_cl <= ang_tol_deg and e_ap <= ang_tol_deg and lat <= lat_tol and z_ok}


# ---------------------------------------------------------------------------------------------- gap table
def rekey(q_rows: list, gaps: list, closed_tol: float = CLOSED_TOL) -> tuple:
    """Rows (q dicts IN PATH ORDER, closed -> open) + their measured gaps -> (kept row indices, gap_m):
    the rows up to the last one with gap <= closed_tol collapse into ONE closed row at gap 0 (the most closed joint
    values = the first row of the path); after it a row is kept only when its gap exceeds the last kept gap (a
    non-monotonic stretch, e.g. a fingertip swinging out of the window, is skipped, never re-ordered); nan rows
    (beyond the window) are dropped. ValueError when fewer than 2 rows remain."""
    fin = [i for i, g in enumerate(gaps) if np.isfinite(g)]
    if not fin:
        raise ValueError("no finite gap on the closing path")
    closed = [i for i in fin if gaps[i] <= closed_tol]
    start = (max(closed) + 1) if closed else 0
    keep, gap_m = ([0], [0.0]) if closed else ([], [])
    for i in fin:
        if i < start:
            continue
        if not gap_m or gaps[i] > gap_m[-1]:
            keep.append(i)
            gap_m.append(round(float(gaps[i]), 5))
    if len(keep) < 2:
        raise ValueError(f"fewer than 2 usable rows: {[round(g, 4) for g in gaps]}")
    return keep, gap_m


def path_order_ok(q_rows: list, gaps: list) -> bool:
    """The measured gap must be monotonic ALONG the closing path (not only after sorting)."""
    g = [x for x in gaps if np.isfinite(x)]
    d = np.diff(g)
    return bool((d >= -1e-4).all() or (d <= 1e-4).all())


class GapTable:
    """Finger joints <-> measured gaps for one gripper side (rows closed -> open). Two measured columns:
    gap_m      -- the FREE gap: the binding slot between the opposing finger chains over the window around the TCP
                  plane (hand9.BANDS): what an object near the TCP must fit through (opening, pre-open, max, empty);
    gap_tcp_m  -- the gap in the TCP plane itself (TCP_BAND): what the settled fingers read on an object grasped at
                  the TCP (contact-width comparison of the close verdict). = gap_m for parallel pads."""

    def __init__(self, d: dict):
        self.name = d.get("name")
        self.joints = list(d["joints"])
        self.Q = np.asarray(d["q"], float)  # (rows, joints)
        self.gap = np.asarray(d["gap_m"], float)
        self.gap_tcp = np.asarray(d.get("gap_tcp_m") or d["gap_m"], float)
        if len(self.gap) < 2 or not (np.diff(self.gap) > 0).all():
            raise ValueError(f"{self.name}: gap table must be strictly increasing with >= 2 rows")
        self.meta = d

    @property
    def max_gap(self) -> float:
        return float(self.gap[-1])

    @property
    def closed_gap(self) -> float:
        return float(self.gap[0])

    def joints_for_gap(self, w: float) -> dict:
        """Finger joint targets for an opening (measured free gap) w; w <= closed -> the closed row."""
        w = float(w)
        return {j: float(np.interp(w, self.gap, self.Q[:, k])) for k, j in enumerate(self.joints)}

    def _project(self, q) -> tuple:
        """(row i, s in [0, 1]) of the nearest point of the closing path (piecewise linear in joint space) to q."""
        if isinstance(q, dict):
            q = [q[j] for j in self.joints]
        q = np.asarray(q, float)
        best, best_d = (0, 0.0), float("inf")
        for i in range(len(self.gap) - 1):
            a, b = self.Q[i], self.Q[i + 1]
            ab = b - a
            L = float(ab @ ab)
            s = 0.0 if L < 1e-18 else float(np.clip((q - a) @ ab / L, 0.0, 1.0))
            d = float(np.linalg.norm(a + s * ab - q))
            if d < best_d:
                best_d, best = d, (i, s)
        return best

    def gap_of_q(self, q) -> float:
        """Measured free gap of finger joints q (dict by name or a vector in self.joints order)."""
        i, s = self._project(q)
        return float(self.gap[i] + s * (self.gap[i + 1] - self.gap[i]))

    def tcp_gap_of_q(self, q) -> float:
        """Measured gap in the TCP plane of finger joints q."""
        i, s = self._project(q)
        return float(self.gap_tcp[i] + s * (self.gap_tcp[i + 1] - self.gap_tcp[i]))

    def exec_offsets(self, w: float) -> dict:
        """Where the fingers actually are, in frame G, when the hand is closed to the opening w (rows interpolated):
        contact_mid = midpoint of the two opposing sides' contact patches (the real grasp centre: the G1 Dex3-1
        meets ~16 mm off the frame origin in x_G), tip_front = the deepest finger point along the approach (z_G,
        negative = ahead; the closing pads' arc drop). For a generic exec_pose (support back-off / lateral
        correction) -- data only, nothing here changes a pose."""
        m = self.meta
        opp = (m.get("method") or {}).get("opposition") or []
        cs = m.get("contacts_G") or []
        out = {}
        if opp and len(cs) == len(self.gap):
            A, B = opp[0]
            mid = np.array([(np.mean([c[t] for t in A], axis=0) + np.mean([c[t] for t in B], axis=0)) / 2
                            for c in cs])
            out["contact_mid"] = [float(np.interp(float(w), self.gap, mid[:, k])) for k in range(3)]
        if len(m.get("tip_front_G") or []) == len(self.gap):
            out["tip_front"] = float(np.interp(float(w), self.gap, m["tip_front_G"]))
        return out

    def is_open(self, gap: float) -> bool:
        return float(gap) >= self.max_gap - OPEN_TOL


_TABLES: dict = {}


def table(name: str) -> GapTable | None:
    """The committed gap table of gripper json `name` (None when it has not been measured)."""
    if name not in _TABLES:
        p = os.path.join(GAP_DIR, f"{name}.json")
        _TABLES[name] = GapTable(dict(json.load(open(p, encoding="utf-8")), name=name)) if os.path.exists(p) else None
    return _TABLES[name]


def table_for(profile: str | None, arm: str) -> GapTable | None:
    """Gap table of a robot profile's arm (profile None = the AI Worker, the L8/L9 default robot)."""
    return table(GRIPPER_JSON.get((profile or "ffw_sg2", arm), ""))


def active_table(profile: str | None, arm: str) -> GapTable | None:
    """The table when the layer is on (L9_GRIP_LAYER=1), else None -> callers keep their old path unchanged."""
    return table_for(profile, arm) if enabled() else None


# ---------------------------------------------------------------------------------------------- verdicts
def close_verdict(gap: float, w_contact: float, closed_gap: float = 0.0, touched=None, target=None,
                  gap_tcp: float | None = None) -> str:
    """Generic close judgement on the MEASURED gaps (every robot, 2- or N-finger):
    EMPTY  -- the hand closed to (within EMPTY_TOL of) its measured closed free gap, or contact data exists and no
              fingertip touches the target;
    CONTACT -- the settled TCP-plane gap (gap_tcp, default = gap) matches the planned contact width (-0.8 / +2.0 cm);
    WIDE   -- anything else."""
    gap = float(gap)
    if gap <= closed_gap + EMPTY_TOL:
        return "EMPTY"
    if touched is not None and target is not None and target not in touched:
        return "EMPTY"
    gc = gap if gap_tcp is None else float(gap_tcp)
    if -CONTACT_TOL <= gc - float(w_contact) <= CONTACT_TOL_HI:
        return "CONTACT"
    return "WIDE"


def holding(tip_forces, joint_efforts, gap: float | None = None, tbl: GapTable | None = None,
            force_min: float = FORCE_MIN_N, effort_min: float = EFFORT_MIN) -> bool:
    """Holding = ANY fingertip / pad in contact (force > force_min) AND the MAX |effort| over ALL finger joints
    >= effort_min AND (with a gap table) not fully open. Never a single joint; 2-finger and N-finger alike."""
    f = np.abs(np.asarray(tip_forces, float)).reshape(-1)
    e = np.abs(np.asarray(joint_efforts, float)).reshape(-1)
    if not len(f) or not len(e):
        return False
    if gap is not None and tbl is not None and tbl.is_open(gap):
        return False
    return bool((f > force_min).any() and e.max() >= effort_min)


def side_of(body: str, tbl: GapTable) -> int | None:
    """0 / 1 = the opposition side whose finger chains contain `body` (first opposition pair), None = neither."""
    m = tbl.meta.get("method", {})
    chains, opp = m.get("chains", {}), m.get("opposition") or []
    if not opp:
        return None
    for k, tips in enumerate(opp[0]):
        if any(body == t or body in chains.get(t, ()) for t in tips):
            return k
    return None


def pinched(forces: dict, tbl: GapTable, force_min: float = FORCE_MIN_N) -> bool:
    """Truth for the A/B count: the object is in contact with BOTH opposing sides (forces = finger contact body ->
    contact force magnitude)."""
    sides = {side_of(b, tbl) for b, f in forces.items() if f > force_min}
    return {0, 1} <= sides


def torso_check(episodes: list, ranges: dict | None = None, still_tol: float = 1e-3, min_spread: float = 0.0) -> dict:
    """(6) episodes: [{joint: [q per step]}] of the torso / lift joints. Per episode: max |q - q[0]| <= still_tol
    (never moved during the episode); across episodes: the per-episode values stay inside `ranges` and (when
    min_spread > 0) spread at least min_spread (random between episodes, within the range)."""
    moved, outside, firsts = [], [], {}
    for i, ep in enumerate(episodes):
        for j, qs in ep.items():
            qs = np.asarray(qs, float)
            if len(qs) and float(np.abs(qs - qs[0]).max()) > still_tol:
                moved.append((i, j, round(float(np.abs(qs - qs[0]).max()), 4)))
            if len(qs):
                firsts.setdefault(j, []).append(float(qs[0]))
                lo_hi = (ranges or {}).get(j)
                if lo_hi and not (lo_hi[0] - still_tol <= qs[0] <= lo_hi[1] + still_tol):
                    outside.append((i, j, round(float(qs[0]), 4)))
    spread = {j: round(max(v) - min(v), 4) for j, v in firsts.items()}
    narrow = [j for j, s in spread.items() if min_spread > 0 and (ranges or {}).get(j) and s < min_spread]
    return {"ok": not moved and not outside and not narrow, "moved": moved[:10], "outside": outside[:10],
            "spread": spread, "narrow": narrow, "n_episodes": len(episodes)}
