"""Truth labels of the point-then-act interface (canon §97 보충 2) -- free in our own sim: the E-TEACH-L8 truth plan
(teach_l8.labels.plan, = astra_solo/truth.py + the recovery rules) mapped onto pt commands, with the pointed pixel
PROJECTED from the simulator object pose through the known head camera and CHECKED against the head depth:
  above_target -> point at the target, height above;   descend_close -> point at the target, height grasp, close
  carry_over   -> point at the place, height above;    lower_open    -> point at the place, height place, open
  lift_clear / carry_up -> height lift;  retreat -> edit +10 cm up;  reopen / done -> as the xyz label.
label_pixel: candidate points on the object's top face (centre, then rings) and body (mid-height ring); the first
whose 0-1000 point RESOLVES (resolve.py, the runtime path) to the object -- footprint centre within XY_TOL and top
within TOP_TOL -- is the label. None when no candidate resolves (hidden object): the row is dropped (prereg_pt §3).
PtTruth = the truth model driving a PtEpisode through the pt interface (the interface's ceiling; never a result
arm). Also the projected TCP / object pixels for the pointing QA (`pixels_of`)."""
from __future__ import annotations

import json
import math

import numpy as np

from ..astra_motion import geometry as G
from ..astra_motion.harness import obj_height
from . import resolve as RS

XY_TOL = 0.012
TOP_TOL = 0.008
STEP_MAP = {"above_target": ("tgt", "above", "keep"), "descend_close": ("tgt", "grasp", "close"),
            "carry_over": ("place", "above", "keep"), "lower_open": ("place", "place", "open"),
            "lift_clear": (None, "lift", "keep"), "carry_up": (None, "lift", "keep")}
ASSESS = {"task_progress": {"verified_completed": [], "currently_attempting": "task", "remaining": []},
          "execution_status": "progressing", "evidence": "ground truth", "evidence_view": "both", "confidence": "high"}


def _radius(key: str) -> float:
    from ..sim.scene import OBJ_GEOM
    return float(OBJ_GEOM[key].get("footprint_r", 0.03))


def candidates(center, key: str) -> list:
    c = np.asarray(center, float)
    h = obj_height(key)
    top = c[2] + h / 2
    r = min(_radius(key), 0.06)
    out = [np.array([c[0], c[1], top])]
    for f in (0.35, 0.7):
        out += [np.array([c[0] + f * r * math.cos(a), c[1] + f * r * math.sin(a), top])
                for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    out += [np.array([c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2]])
            for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    return out


def label_pixel(cam, depth, table_z: float, center, key: str):
    """-> (point_2d [x, y] on the 0-1000 scale, info) or (None, info)."""
    c = np.asarray(center, float)
    top = c[2] + obj_height(key) / 2
    flat = obj_height(key) < 2 * RS.H_MIN  # e.g. the 2 mm marker: a table point
    for k, p in enumerate(candidates(c, key)):
        u, v, z = G.project(cam, p)
        if z <= 0 or not (0 <= u < cam.W and 0 <= v < cam.H):
            continue
        pt = RS.to_scaled(u, v, cam.W, cam.H)
        r = RS.resolve_point(cam, depth, table_z, pt)
        if r["xy"] is None:
            continue
        exy = float(np.hypot(r["xy"][0] - c[0], r["xy"][1] - c[1]))
        ok = exy <= XY_TOL and ((r["kind"] == "object" and abs(r["top"] - top) <= TOP_TOL) or
                                (flat and r["kind"] == "table"))
        if ok:
            return pt, {"cand": k, "xy_err_mm": round(exy * 1e3, 1),
                        "top_err_mm": None if r["top"] is None else round((r["top"] - top) * 1e3, 1)}
    return None, {"cand": None}


def pt_command(step: str, xyz_cmd: dict, st: dict, info: dict, cam, depth, table_z: float):
    """(pt command dict | None, info). None = no verified pixel for a point step (the row is dropped)."""
    if step in STEP_MAP:
        role, h, g = STEP_MAP[step]
        if role is None:
            return {"mode": "point", "point_2d": None, "height": h, "gripper": g}, {}
        key = info[role]
        pt, meta = label_pixel(cam, depth, table_z, st["obj"][key], key)
        if pt is None:
            return None, meta
        return {"mode": "point", "point_2d": pt, "height": h, "gripper": g}, meta
    if step == "retreat":
        return {"mode": "edit", "delta_m": [0.0, 0.0, 0.10], "gripper": "keep"}, {}
    return dict(xyz_cmd), {}  # reopen (gripper open) / done (stop)


def pixels_of(cam, st: dict, info: dict) -> dict:
    """Projected 0-1000 points (None when outside) of the TCP, its drop point on the table and every object centre."""
    out = {}

    def px(p):
        u, v, z = G.project(cam, p)
        return RS.to_scaled(u, v, cam.W, cam.H) if z > 0 and 0 <= u < cam.W and 0 <= v < cam.H else None
    t = np.asarray(st["tcp"], float)
    out["tcp"] = px(t)
    for k, c in st["obj"].items():
        out[k] = px(c)
    return out


class PtTruth:
    """Truth model through the pt interface: needs the running PtEpisode (its depth / head camera of this call)."""
    name = "truth-pt"

    def __init__(self, world):
        self.w, self.ep = world, None

    def ask(self, text, images, meta):
        from ..astra_motion.truth import Rep
        from ..teach_l8.labels import plan
        ep = self.ep
        st = self.w.status()
        step, cmd = plan(st, ep.info, self.w.table_z, self.w.w_open)
        if cmd is None:
            c = {"mode": "stop"}
        else:
            c, _ = pt_command(step, cmd, st, ep.info, ep.head, ep.depth, self.w.table_z)
            if c is None:  # no verified pixel: point at the projected top centre anyway
                p = np.asarray(st["obj"][ep.info[STEP_MAP[step][0]]], float)
                u, v, _ = G.project(ep.head, p)
                c = {"mode": "point", "point_2d": RS.to_scaled(u, v, ep.head.W, ep.head.H),
                     "height": STEP_MAP[step][1], "gripper": STEP_MAP[step][2]}
        if c.get("point_2d") is None:
            c = {k: v for k, v in c.items() if k != "point_2d"}
        return Rep(json.dumps({"assessment": ASSESS, "command": c, "reason": f"truth {step}"}))


class NdTruth:
    """Truth model through the no-depth interfaces (nd-xyz / nd-est: the xyz truth; nd-pt: nd.nd_pt_command) with the
    simulator estimates block -- the interface ceiling and the wiring check; never a result arm."""

    def __init__(self, world, iface: str):
        self.w, self.iface, self.ep = world, iface, None
        self.name = f"truth-{iface}"

    def ask(self, text, images, meta):
        from ..astra_motion.truth import Rep
        from ..teach_l8.labels import plan
        from .nd import est_label, nd_pt_command
        ep, w = self.ep, self.w
        st = w.status()
        step, cmd = plan(st, ep.info, w.table_z, w.w_open)
        c = {"mode": "stop"} if cmd is None else dict(cmd)
        if cmd is not None and self.iface == "nd-pt":
            c2, _ = nd_pt_command(step, cmd, st, ep.info, ep.head)
            c = c2 if c2 is not None else {"mode": "stop"}
        out = {"assessment": ASSESS, "command": c, "reason": f"truth {step}"}
        if self.iface in ("nd-est", "nd-pt"):
            out = {"estimates": est_label(st, ep.info, w.table_z), **out}
        return Rep(json.dumps(out))
