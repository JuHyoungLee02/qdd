"""Articulated-episode scenes in the World9 format (pure): one table (scene9 / furniture parts), the fixture on it
facing the robot, task / prop objects, the lift. World9.reset builds rooms, materials, lights, HDRI and the head
camera from these dicts exactly as for L9 v2 pick-place episodes.

Frames: robot / world frame (x forward, y left, z up); the fixture pose T_WF = (Rz(yaw), (x_face, y_f, tz)): its
front-bottom centre on the table top, its front facing the robot within +-12 deg."""
from __future__ import annotations

import math

import numpy as np

from . import fixtures as FX

FAMILIES_ENV = ("kitchen", "office", "living_low", "dining", "workbench", "entrance")
LIFT_DEFAULT = -0.0993
H_REF = 0.92  # [가설] interaction height at the default lift (L8S table 0.78 + 0.14; xdrawer used 0.95 for drawers)
TZ = (0.70, 0.84)
YAW = math.radians(12.0)
BAND_Y = (-0.34, -0.10)  # right arm: the handle / knob / button y band (left arm mirrored)
FACE_X = {"drawer": (0.50, 0.58), "door": (0.52, 0.60), "slide": (0.48, 0.56), "knob": (0.44, 0.52),
          "button": (0.44, 0.52), "panel": (0.44, 0.52)}
TOP_FACE_X = (0.30, 0.38)  # knob / button panels with top-mounted parts: their front edge


def side(arm: str) -> int:
    return 1 if arm == "right" else -1


def T_WF(x, y, z, yaw) -> np.ndarray:
    return FX.T_of(FX.rot_axis([0, 0, 1], yaw), (x, y, z))


def place_fixture(spec: dict, prog: dict, arm: str, tz: float, rng) -> dict:
    """Fixture pose: the program's first part in the arm band, the face at FACE_X; -> {T, yaw, pos}."""
    yaw = float(rng.uniform(-YAW, YAW))
    fam = spec["family"]
    ln = next((s["link"] for s in prog["stages"] if s.get("link")), None) or next(iter(spec["handles"]))
    h = spec["handles"][ln]
    top = h.get("face") == "top"
    x_face = float(rng.uniform(*(TOP_FACE_X if top else FACE_X[fam])))
    hy = float((FX.link_T(spec, ln)[:3, :3] @ np.asarray(h["gc"]) + FX.link_T(spec, ln)[:3, 3])[1])
    yb = float(rng.uniform(*BAND_Y)) * side(arm)
    y_f = yb - hy * math.cos(yaw)
    T = T_WF(x_face, y_f, tz, yaw)
    return {"T": T.tolist(), "yaw": round(yaw, 5), "pos": [round(x_face, 4), round(y_f, 4), round(tz, 4)]}


WS_X = (0.27, 0.66)  # [가설] comfortable TCP box of a 7-DoF arm at the L9 robot poses (refined by the cuRobo IK check)
WS_Y = (-0.52, 0.06)  # right arm (left mirrored)
WS_DZ = (0.02, 0.50)


def path_points(spec: dict, prog: dict, T, n: int = 6) -> np.ndarray:
    """Grasp / contact points of every joint stage from its start to its goal (world)."""
    pts = []
    q = {jn: 0.0 for jn in spec["joints"]}
    for jn, v in prog["start"].items():
        q[jn] = v
    for st in prog["stages"]:
        if not st.get("link"):
            continue
        jn = spec["handles"][st["link"]]["joint"]
        q0 = q[jn]
        g = st["goal"] if st.get("goal") is not None else q0
        for s in np.linspace(0, 1, n):
            qq = dict(q, **{jn: q0 + s * (g - q0)})
            pts.append(FX.handle_frame(spec, st["link"], T, qq)["gc"])
        q[jn] = g
    return np.asarray(pts)


def in_ws(pts, arm: str, tz: float) -> bool:
    y = pts[:, 1] * side(arm)
    return bool((pts[:, 0] >= WS_X[0]).all() and (pts[:, 0] <= WS_X[1]).all() and (y >= WS_Y[0]).all()
                and (y <= WS_Y[1]).all() and (pts[:, 2] >= tz + WS_DZ[0]).all() and (pts[:, 2] <= tz + WS_DZ[1]).all())


def fixture_aabb(spec: dict, T, margin: float = 0.0) -> tuple:
    x0, x1, y0, y1 = FX.footprint(spec, margin)
    P = np.array([[x, y, 0.0, 1.0] for x in (x0, x1) for y in (y0, y1)]) @ np.asarray(T, float).T
    return (float(P[:, 0].min()), float(P[:, 0].max())), (float(P[:, 1].min()), float(P[:, 1].max()))


def interaction_z(spec: dict | None, prog: dict, T, tz: float) -> float:
    if spec is None:
        return tz + 0.08
    zs = []
    for s in prog["stages"]:
        if s.get("link"):
            hf = FX.handle_frame(spec, s["link"], T)
            zs.append(float(hf["gc"][2]))
    return float(np.mean(zs)) if zs else tz + 0.1


HEAD_XZ = (0.05, 1.45)  # [가설] AI Worker head camera (x, z) at the default lift
PAN_MAX, TILT_LIM = 0.34, (0.40, 0.98)


def head_aim(seed: int, p_int, lift: float) -> dict:
    """AI Worker neck pose looking at the interaction point (+ small jitter) so the part and its goal stay in view
    (smoke 10-02: random pans left handles / push goals outside the head image). Pan > 0 = to the robot's left."""
    rng = np.random.default_rng([int(seed), 7171])
    x, y, z = (float(v) for v in p_int)
    zh = HEAD_XZ[1] + (lift - LIFT_DEFAULT)
    pan = float(np.clip(math.atan2(y, max(0.1, x - HEAD_XZ[0])) + rng.uniform(-0.08, 0.08), -PAN_MAX, PAN_MAX))
    tilt = float(np.clip(math.atan2(zh - z, max(0.1, x - HEAD_XZ[0])) + rng.uniform(-0.10, 0.10), *TILT_LIM))
    return {"tilt": round(tilt, 4), "pan": round(pan, 4), "random": True, "aimed": True}


def lift_for(z_int: float, rng) -> float:
    return float(np.clip(LIFT_DEFAULT + (z_int - H_REF) + rng.uniform(-0.02, 0.02), -0.5, 0.0))


def build(seed: int, robot: str, arm: str, spec: dict | None, prog: dict, objs: dict) -> dict:
    """seed -> {sc, ep, fixture {T, yaw, pos}, objects}. objs: {key: {"name", "fp": (dx, dy), "h"}} candidates (the
    first is the task / prop object). Raises ValueError when nothing fits."""
    from ..sim.assets_x.furniture import _table
    rng = np.random.default_rng([int(seed), 6061])
    tz = float(rng.uniform(*TZ))
    fx = None
    if spec is not None:  # the whole handle path (start -> goal of every stage) inside the arm's box
        for _ in range(40):
            fx = place_fixture(spec, prog, arm, tz, rng)
            if in_ws(path_points(spec, prog, np.asarray(fx["T"])), arm, tz):
                break
        else:
            raise ValueError("no placement keeps the handle path inside the arm's workspace")
    sg = side(arm)
    x_front = float(rng.uniform(0.20, 0.27))
    if fx is not None:
        (ax0, ax1), (ay0, ay1) = fixture_aabb(spec, fx["T"], 0.02)
        x_back = max(ax1 + float(rng.uniform(0.04, 0.15)), x_front + 0.55)
        y_lo, y_hi = min(ay0 - 0.30, -0.55 if sg > 0 else -0.25) - 0.05, max(ay1 + 0.30, 0.25 if sg > 0 else 0.55) + 0.05
    else:
        x_back = x_front + float(rng.uniform(0.55, 0.8))
        y_lo, y_hi = -0.6, 0.6
    W = y_hi - y_lo
    extra = float(rng.uniform(0.0, 0.3))
    y_lo, y_hi = y_lo - extra * rng.random(), y_hi + extra * rng.random()
    col = tuple(float(c) for c in FX.WOOD[int(rng.integers(len(FX.WOOD)))])
    parts = _table(rng, "t0", tz, x_front, x_back - x_front, y_lo, y_hi, col)
    for p in parts:
        p["mat_hint"] = "wood"
    node = {"id": "n0", "kind": "top", "part": "t0", "top_z": round(tz, 4), "box": [[x_front, x_back], [y_lo, y_hi]],
            "rim_z": None, "place_class": "desk"}
    family = FAMILIES_ENV[int(rng.integers(len(FAMILIES_ENV)))]
    z_int = interaction_z(spec, prog, fx["T"] if fx else None, tz)
    lift = lift_for(z_int, rng)
    # objects: free table spots in front of / beside the fixture (push / prop / combo source)
    keep_out = fixture_aabb(spec, fx["T"], 0.06) if fx is not None else None
    placed = {}
    take = prog["def"] == "drawer_take_close"
    objs_l = dict(objs)
    if take:  # a free table spot for the object taken out of the drawer
        objs_l["__spot"] = {"name": "spot", "fp": (0.09, 0.09), "h": 0.0}
    y_h = None
    if fx is not None:
        ln0 = next((s["link"] for s in prog["stages"] if s.get("link")), None)
        if ln0:
            y_h = float(FX.handle_frame(spec, ln0, np.asarray(fx["T"]))["gc"][1])
    for k, o in objs_l.items():
        dx, dy = o["fp"]
        r = 0.5 * math.hypot(dx, dy) + 0.02
        ok = False
        for _ in range(60):
            near = False
            if prog.get("need_obj") == "pushable" and not placed:
                x = float(rng.uniform(0.33, 0.45))
                y = float(rng.uniform(*BAND_Y)) * sg
            elif prog.get("need_obj") == "small" and (not placed or k == "__spot") and y_h is not None:
                x = float(rng.uniform(0.30, 0.46))  # within reach beside the fixture's front (combo pick / put)
                y = y_h + float(rng.choice([-1, 1])) * float(rng.uniform(0.14, 0.24))
                if not (WS_Y[0] + 0.04 <= y * sg <= WS_Y[1] - 0.02):
                    continue
                near = True
            else:
                x = float(rng.uniform(x_front + 0.08, max(x_front + 0.1, min(x_back - 0.08, 0.70))))
                y = float(rng.uniform(y_lo + 0.08, y_hi - 0.08))
            if keep_out is not None:
                (kx0, kx1), (ky0, ky1) = keep_out
                if kx0 - r < x < kx1 + r and ky0 - r < y < ky1 + r:
                    continue
                if not near and fx is not None and x < kx0 + 0.05 and abs(y - np.asarray(fx["T"])[1][3]) < 0.25:
                    continue  # the corridor in front of the fixture stays free for the arm
            if any(math.hypot(x - p[0], y - p[1]) < r + q for p, q in placed.values()):
                continue
            placed[k] = ((x, y), r)
            ok = True
            break
        if not ok and not placed:
            raise ValueError("no free table spot for the object")
    if not placed:
        raise ValueError("no object")
    spot = placed.pop("__spot", None)
    if take and spot is None:
        raise ValueError("no free table spot to put the object")
    keys = list(placed)
    tgt = keys[0]
    objects = {k: {"xy": [round(placed[k][0][0], 4), round(placed[k][0][1], 4)], "node": "n0"} for k in keys}
    spot_xy = [objects[tgt]["xy"][0] + 0.001, objects[tgt]["xy"][1]]
    nodes = [node]
    if take:  # the object starts on the drawer floor, in its front part (exposed once the drawer is open)
        ln = prog["stages"][0]["link"]
        it = spec["interior"][ln]
        Tl = np.asarray(fx["T"]) @ FX.link_T(spec, ln)
        dx = float(objs[tgt]["fp"][0])
        pw = Tl @ np.array([0.035 + dx / 2, 0.0, it["floor_c"][2], 1.0])
        objects[tgt] = {"xy": [round(float(pw[0]), 4), round(float(pw[1]), 4)], "node": "n_drw"}
        nodes.append({"id": "n_drw", "kind": "container", "part": None, "top_z": round(float(pw[2]), 4),
                      "box": [[float(pw[0]) - 0.05, float(pw[0]) + 0.05], [float(pw[1]) - 0.05, float(pw[1]) + 0.05]],
                      "rim_z": None, "place_class": "desk"})
        spot_xy = [round(spot[0][0], 4), round(spot[0][1], 4)]
    ep = {"def": prog["def"], "family": "articulated", "table_z": round(tz, 4), "main": "n0", "objects": objects,
          "spots": {"s9_0": {"xy": spot_xy, "rule_text": "beside it"}}, "surfaces": {}, "clutter": {},
          "steps": [(tgt, "s9_0", None)], "instruction": prog["instruction"], "template": prog["def"],
          "names": {k: objs[k]["name"] for k in keys}}
    sc = {"family": family, "rule": "art", "seed": int(seed), "arm": arm, "try": 0, "yaw": 0.0,
          "robot_pose": {"distance": round(x_front, 4), "yaw": 0.0}, "params": {"art": True}, "furniture": parts,
          "nodes": nodes, "lift": round(lift, 4), "usable_n": {"n0": 99}}
    if fx is not None:
        P = path_points(spec, prog, np.asarray(fx["T"]))
        p_int = P.mean(0) if len(P) else np.asarray(fx["T"])[:3, 3]
    else:
        p_int = np.array([objects[tgt]["xy"][0] + 0.05, objects[tgt]["xy"][1], tz + 0.05])
    return {"sc": sc, "ep": ep, "fixture": fx, "tz": tz, "z_int": round(z_int, 4), "tgt": tgt, "spot_xy": spot_xy,
            "p_int": [round(float(v), 4) for v in p_int]}
