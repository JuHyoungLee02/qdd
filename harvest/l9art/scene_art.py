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


def lift_for(z_int: float, rng) -> float:
    return float(np.clip(LIFT_DEFAULT + (z_int - H_REF) + rng.uniform(-0.02, 0.02), -0.5, 0.0))


def build(seed: int, robot: str, arm: str, spec: dict | None, prog: dict, objs: dict) -> dict:
    """seed -> {sc, ep, fixture {T, yaw, pos}, objects}. objs: {key: {"name", "fp": (dx, dy), "h"}} candidates (the
    first is the task / prop object). Raises ValueError when nothing fits."""
    from ..sim.assets_x.furniture import _table
    rng = np.random.default_rng([int(seed), 6061])
    tz = float(rng.uniform(*TZ))
    fx = place_fixture(spec, prog, arm, tz, rng) if spec is not None else None
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
    for k, o in objs.items():
        dx, dy = o["fp"]
        r = 0.5 * math.hypot(dx, dy) + 0.02
        ok = False
        for _ in range(60):
            if prog.get("need_obj") == "pushable" and not placed:
                x = float(rng.uniform(0.33, 0.45))
                y = float(rng.uniform(*BAND_Y)) * sg
            else:
                x = float(rng.uniform(x_front + 0.08, max(x_front + 0.1, min(x_back - 0.08, 0.70))))
                y = float(rng.uniform(y_lo + 0.08, y_hi - 0.08))
            if keep_out is not None:
                (kx0, kx1), (ky0, ky1) = keep_out
                if kx0 - r < x < kx1 + r and ky0 - r < y < ky1 + r:
                    continue
                if fx is not None and x < kx0 + 0.05 and abs(y - np.asarray(fx["T"])[1][3]) < 0.25:
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
    keys = list(placed)
    tgt = keys[0]
    objects = {k: {"xy": [round(placed[k][0][0], 4), round(placed[k][0][1], 4)], "node": "n0"} for k in keys}
    spot_xy = [objects[tgt]["xy"][0] + 0.001, objects[tgt]["xy"][1]]
    ep = {"def": prog["def"], "family": "articulated", "table_z": round(tz, 4), "main": "n0", "objects": objects,
          "spots": {"s9_0": {"xy": spot_xy, "rule_text": "beside it"}}, "surfaces": {}, "clutter": {},
          "steps": [(tgt, "s9_0", None)], "instruction": prog["instruction"], "template": prog["def"],
          "names": {k: objs[k]["name"] for k in keys}}
    sc = {"family": family, "rule": "art", "seed": int(seed), "arm": arm, "try": 0, "yaw": 0.0,
          "robot_pose": {"distance": round(x_front, 4), "yaw": 0.0}, "params": {"art": True}, "furniture": parts,
          "nodes": [node], "lift": round(lift, 4), "usable_n": {"n0": 99}}
    return {"sc": sc, "ep": ep, "fixture": fx, "tz": tz, "z_int": round(z_int, 4), "tgt": tgt}
