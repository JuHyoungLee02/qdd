"""Typed answer of the astra-solo-pt@v1 interface (point then act, canon §97 보충 2), checked by code.

Same assessment as astra-solo@v2 (schema.py); the command modes are
  point   {"mode": "point", "point_2d": [x, y], "height": "above" | "grasp" | "place" | "lift", "gripper": ...}
          point_2d on the 0-1000 scale of image 1 (x right, y down); required except for height lift (ignored there);
          an omitted / null gripper = keep (recorded as gripper_defaulted, pitfall P106)
  edit    as v2 (relative correction, |delta| <= 0.10 m, a longer one is shortened and reported)
  gripper as v2
  stop    as v2
There is no absolute-coordinate mode for the model. allow_eef=True (collection only: the scripted behaviour policy
drives the episode with v2 eef commands) also accepts v2's eef."""
from __future__ import annotations

import math

from ..astra_motion.schema import SchemaError, extract_json
from . import schema as V2
from .resolve import INTENTS, SCALE

MODES = ("point", "edit", "gripper", "stop")


def _point(c, err):
    v = c.get("point_2d")
    if not isinstance(v, list) or len(v) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float))
                                                     or not math.isfinite(x) for x in v):
        err.append("command.point_2d: not a list of 2 numbers")
        return None
    if any(not 0 <= x <= SCALE for x in v):
        err.append(f"command.point_2d={v}: outside 0..{SCALE:.0f}")
        return None
    return [float(x) for x in v]


def _command(d, err, allow_eef):
    c = d.get("command")
    if not isinstance(c, dict):
        err.append("command: missing")
        return None
    if allow_eef and c.get("mode") == "eef":
        return V2._command(d, err)
    mode = V2._enum(c, "mode", MODES, err, "command")
    if mode == "edit":
        return V2._command(d, err)
    out = {"mode": mode}
    if mode == "point":
        if c.get("gripper") is None:
            c = dict(c, gripper="keep")
            out["gripper_defaulted"] = True
        out["height"] = V2._enum(c, "height", INTENTS, err, "command")
        out["point_2d"] = None if out["height"] == "lift" and c.get("point_2d") is None else _point(c, err)
        out["gripper"] = V2._enum(c, "gripper", V2.GRIPPER, err, "command")
    elif mode == "gripper":
        out["gripper"] = V2._enum(c, "gripper", ("open", "close"), err, "command")
    return out


def validate(text: str, allow_eef: bool = False):
    """(parsed, []) or (None, [errors])."""
    err: list = []
    try:
        d = extract_json(text)
    except SchemaError as e:
        return None, [str(e)]
    out = {"assessment": V2._assessment(d, err), "command": _command(d, err, allow_eef),
           "reason": str(d.get("reason", ""))[:400]}
    return (out, []) if not err else (None, err)
