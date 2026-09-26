"""No-depth (ND) arms of E-PT (prereg_pt.md §1): schema, truth labels, the ring-only head image and the no-depth
point resolver. Prompts: nd_prompts.py.
  estimates (nd-est / nd-pt): {"table_z", "target_base_xy" [x, y], "target_height_m", "target_width_m", "place_xy"
      [x, y], "place_top_z"} -- labels from the simulator (free), never from depth at run time.
  nd-pt point: {"mode": "point", "point_2d": [x, y] (0-1000, on the TOP of the object), "top_z": m, "height",
      "gripper"}; code lifts the pixel ray to z = top_z (the model's estimate) -> xy; the height recipe as
      resolve.target_of with the model's table_z as the plane (lift) and the grip offset measured against it."""
from __future__ import annotations

import math

import numpy as np

from ..astra_motion.geometry import lift_plane
from ..astra_motion.harness import obj_height
from ..astra_motion.schema import SchemaError, extract_json
from . import pt_schema as PS
from . import resolve as RS
from . import schema as V2

EST_KEYS = {"table_z": 1, "target_base_xy": 2, "target_height_m": 1, "target_width_m": 1, "place_xy": 2,
            "place_top_z": 1}


def _num(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _estimates(d, err):
    e = d.get("estimates")
    if not isinstance(e, dict):
        err.append("estimates: missing")
        return None
    out = {}
    for k, n in EST_KEYS.items():
        v = e.get(k)
        ok = (_num(v) if n == 1 else isinstance(v, list) and len(v) == n and all(_num(x) for x in v))
        if not ok:
            err.append(f"estimates.{k}: not {'a number' if n == 1 else f'a list of {n} numbers'}")
        else:
            out[k] = float(v) if n == 1 else [float(x) for x in v]
    return out


def validate(text: str, version: str, allow_eef: bool = False):
    """(parsed, []) or (None, [errors]) for nd-xyz@v1 / nd-est@v1 / nd-pt@v1."""
    if version == "nd-xyz@v1":
        return V2.validate(text)
    err: list = []
    try:
        d = extract_json(text)
    except SchemaError as e:
        return None, [str(e)]
    est = _estimates(d, err)
    if version == "nd-est@v1":
        cmd = V2._command(d, err)
    elif version == "nd-pt@v1":
        cmd = PS._command(d, err, allow_eef)
        if cmd and cmd.get("mode") == "point" and cmd.get("height") != "lift":
            tz = (d.get("command") or {}).get("top_z")
            if not _num(tz):
                err.append("command.top_z: not a number")
            else:
                cmd["top_z"] = float(tz)
    else:
        raise ValueError(version)
    out = {"estimates": est, "assessment": V2._assessment(d, err), "command": cmd,
           "reason": str(d.get("reason", ""))[:400]}
    return (out, []) if not err else (None, err)


def _width(k: str) -> float:
    from ..sim.scene import OBJ_GEOM
    g = OBJ_GEOM[k]
    return float(2 * g["radius"]) if "radius" in g else float(min(g["size"][0], g["size"][1]))


def est_label(st: dict, info: dict, table_z: float) -> dict:
    tg, pl = info["tgt"], info["place"]
    c, p = np.asarray(st["obj"][tg], float), np.asarray(st["obj"][pl], float)
    return {"table_z": round(table_z, 3), "target_base_xy": [round(float(c[0]), 3), round(float(c[1]), 3)],
            "target_height_m": round(obj_height(tg), 3), "target_width_m": round(_width(tg), 3),
            "place_xy": [round(float(p[0]), 3), round(float(p[1]), 3)],
            "place_top_z": round(float(p[2] + obj_height(pl) / 2), 3)}


def nd_pt_command(step: str, xyz_cmd: dict, st: dict, info: dict, cam):
    """nd-pt truth command: pt_truth's step mapping; the pixel = the projection of the centre of the object's TOP
    face (the geometric truth, also when the gripper hides it -- no depth is used) and top_z = its simulator height.
    None when that point projects outside the image."""
    from ..astra_motion.geometry import project
    from .pt_truth import STEP_MAP
    if step not in STEP_MAP:
        if step == "retreat":
            return {"mode": "edit", "delta_m": [0.0, 0.0, 0.10], "gripper": "keep"}, {}
        return dict(xyz_cmd), {}
    role, h, g = STEP_MAP[step]
    if role is None:
        return {"mode": "point", "height": h, "gripper": g}, {}
    key = info[role]
    c = np.asarray(st["obj"][key], float)
    top = float(c[2] + obj_height(key) / 2)
    u, v, z = project(cam, [c[0], c[1], top])
    if z <= 0 or not (0 <= u < cam.W and 0 <= v < cam.H):
        return None, {"why": "outside"}
    return {"mode": "point", "point_2d": RS.to_scaled(u, v, cam.W, cam.H), "top_z": round(top, 3), "height": h,
            "gripper": g}, {}


def resolve_est(cam, cmd: dict, est_table_z: float, tcp, holding: bool, grip_offset):
    """-> (goal [x, y, z] or None, info) with the model's own heights only (no depth)."""
    if cmd["height"] == "lift":
        g, notes = RS.target_of("lift", None, est_table_z, tcp, holding, grip_offset)
        return g, {"goal": g, "notes": notes}
    iu, iv = RS.to_pixel(cmd["point_2d"], cam.W, cam.H)
    q = lift_plane(cam, iu, iv, cmd["top_z"])
    if q is None:
        return None, {"goal": None, "kind": "none"}
    res = {"xy": [float(q[0]), float(q[1])], "top": float(cmd["top_z"])}
    g, notes = RS.target_of(cmd["height"], res, est_table_z, tcp, holding, grip_offset)
    return g, dict(res, goal=[round(v, 4) for v in g], notes=notes)


def ring_overlay(img: np.ndarray, cam, tcp):
    """Head image with the TCP ring only (robot self-information); -> (annotated copy, drawn names)."""
    from PIL import Image, ImageDraw

    from .overlay import BLACK, WHITE, _inside, _px
    im = Image.fromarray(np.ascontiguousarray(img).copy()).convert("RGB")
    d = ImageDraw.Draw(im)
    top = _px(cam, np.asarray(tcp, float))
    drawn = []
    if _inside(cam, top):
        d.ellipse([top[0] - 8, top[1] - 8, top[0] + 8, top[1] + 8], outline=BLACK, width=4)
        d.ellipse([top[0] - 8, top[1] - 8, top[0] + 8, top[1] + 8], outline=WHITE, width=2)
        drawn.append("tcp")
    return np.asarray(im), drawn
