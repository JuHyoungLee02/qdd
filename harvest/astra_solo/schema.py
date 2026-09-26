"""Typed answer of the Astra-solo arm, checked by code (one repair call per call site).

Command modes follow GPT-as-Policy's direct-control modes (J. Su et al. 2026, "GPT 6 Astra as an Embodied Policy":
`eef` = absolute end-effector target, `edit` = relative correction, `stop`), adapted for Astra alone:
  eef     {"mode": "eef", "position_m": [x, y, z], "gripper": "keep" | "open" | "close"}  absolute TCP target in the
          robot base frame; no distance limit (the workspace box clips it, reported, not rejected -- pitfall P62);
          the gripper action runs after arrival.
  edit    {"mode": "edit", "delta_m": [dx, dy, dz], "gripper": ...}  relative to the commanded target, |delta| <= 0.10
          m (a longer delta is scaled to 0.10 m and reported, not rejected).
          On eef / edit an omitted (or null) gripper means keep (recorded as gripper_defaulted).
  gripper {"mode": "gripper", "gripper": "open" | "close"}  act in place.
  stop    {"mode": "stop"}  the task is done (or cannot be done).
Orientation stays top-down (the executor's fixed grasp yaw; the target objects are upright cylinders).
assessment = {task_progress {verified_completed [str], currently_attempting str, remaining [str]}, execution_status,
evidence str, evidence_view head | right_wrist | both, confidence low | medium | high}.
"""
from __future__ import annotations

import math

import numpy as np

from ..astra_motion.schema import SchemaError, extract_json

MODES = ("eef", "edit", "gripper", "stop")
GRIPPER = ("keep", "open", "close")
EXEC_STATUS = ("not_started", "progressing", "failed", "uncertain", "recovered")
VIEWS = ("head", "right_wrist", "both")
CONFIDENCE = ("low", "medium", "high")
EDIT_MAX_M = 0.10


def _vec3(d, k, err, where):
    v = d.get(k) if isinstance(d, dict) else None
    if not isinstance(v, list) or len(v) != 3 or any(isinstance(x, bool) or not isinstance(x, (int, float))
                                                     or not math.isfinite(x) for x in v):
        err.append(f"{where}.{k}: not a list of 3 numbers")
        return None
    return [float(x) for x in v]


def _enum(d, k, allowed, err, where):
    g = d.get(k) if isinstance(d, dict) else None
    if g not in allowed:
        err.append(f"{where}.{k}={g!r} not in {allowed}")
    return g


def _assessment(d, err):
    a = d.get("assessment")
    if not isinstance(a, dict):
        err.append("assessment: missing")
        return None
    tp = a.get("task_progress")
    ok = (isinstance(tp, dict) and isinstance(tp.get("verified_completed"), list)
          and isinstance(tp.get("remaining"), list) and isinstance(tp.get("currently_attempting"), str))
    if not ok:
        err.append("assessment.task_progress: needs verified_completed [str], currently_attempting str, remaining [str]")
    return {"task_progress": tp if ok else None,
            "execution_status": _enum(a, "execution_status", EXEC_STATUS, err, "assessment"),
            "evidence": str(a.get("evidence", ""))[:400],
            "evidence_view": _enum(a, "evidence_view", VIEWS, err, "assessment"),
            "confidence": _enum(a, "confidence", CONFIDENCE, err, "assessment")}


def _command(d, err):
    c = d.get("command")
    if not isinstance(c, dict):
        err.append("command: missing")
        return None
    mode = _enum(c, "mode", MODES, err, "command")
    out = {"mode": mode}
    if mode in ("eef", "edit") and c.get("gripper") is None:  # omitted gripper on a move = keep (recorded; S1 dry run)
        c = dict(c, gripper="keep")
        out["gripper_defaulted"] = True
    if mode == "eef":
        out["position_m"] = _vec3(c, "position_m", err, "command")
        out["gripper"] = _enum(c, "gripper", GRIPPER, err, "command")
    elif mode == "edit":
        dp = _vec3(c, "delta_m", err, "command")
        out["scaled"] = False
        if dp is not None and np.linalg.norm(dp) > EDIT_MAX_M:
            dp = (np.asarray(dp) * (EDIT_MAX_M / np.linalg.norm(dp))).tolist()
            out["scaled"] = True
        out["delta_m"] = dp
        out["gripper"] = _enum(c, "gripper", GRIPPER, err, "command")
    elif mode == "gripper":
        out["gripper"] = _enum(c, "gripper", ("open", "close"), err, "command")
    return out


def validate(text: str):
    """(parsed, []) or (None, [errors])."""
    err: list = []
    try:
        d = extract_json(text)
    except SchemaError as e:
        return None, [str(e)]
    out = {"assessment": _assessment(d, err), "command": _command(d, err), "reason": str(d.get("reason", ""))[:400]}
    return (out, []) if not err else (None, err)
