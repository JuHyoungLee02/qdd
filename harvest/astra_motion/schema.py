"""Typed JSON outputs of the probe, checked by code (violations counted, one repair call allowed in synchronous S).

S-cmd (synchronous S and staggered F0) -- GPT-as-Policy-style control (Su et al. 2026, "GPT 6 Astra as an Embodied
Policy", gate prompt + validation.py / action_edit_kinematics.py):
  {"assessment": {task_progress, current_subgoal, execution_status, execution_evidence, intent_status,
                  intent_evidence},
   "decision": "continue" | "edit" | "stop",
   "edit": {"delta_position_cm": [3] (norm <= 5 cm), "delta_rotation_rad": [3] (optional, norm <= 0.35 rad),
            "gripper": "keep" | "open" | "close"}   (edit only),
   "reason": str}
  Differences from the original: no student policy, so edit is how the arm moves (no "takeover only when failed /
  misaligned" rule); continue = repeat the last committed motion (see prompts); no absolute eef target.
S-diff (staggered F1, flow-anchored): {"assessment", "decision": "keep" | "revise", "command": {"decision": "edit" |
  "stop", "edit": {...}} (revise only), "evidence": non-empty str}.
task_progress = {"verified_completed": [str], "currently_attempting": str, "remaining": [str]}.
"""
from __future__ import annotations

import json
import math
import re

import numpy as np

GRIPPER = ("open", "close", "keep")
EXEC_STATUS = ("not_started", "progressing", "failed", "uncertain", "recovered")
INTENT_STATUS = ("aligned", "misaligned", "uncertain")
DECISIONS = ("continue", "edit", "stop")
CONFIDENCE = ("low", "medium", "high")
EDIT_MAX_CM = 5.0
ROT_MAX_RAD = 0.35


class SchemaError(ValueError):
    pass


def extract_json(text: str) -> dict:
    t = re.sub(r"```(?:json)?", "", text or "")
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        raise SchemaError("json: no object found")
    try:
        d = json.loads(t[a:b + 1])
    except json.JSONDecodeError as e:
        raise SchemaError(f"json: {e.msg}") from None
    if not isinstance(d, dict):
        raise SchemaError("json: top level is not an object")
    return d


def _vec3(d, k, err, where, required=True):
    v = d.get(k) if isinstance(d, dict) else None
    if v is None and not required:
        return [0.0, 0.0, 0.0]
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


def _progress(d, err):
    tp = d.get("task_progress") if isinstance(d, dict) else None
    if not isinstance(tp, dict):
        err.append("task_progress: missing")
        return None
    ok = (isinstance(tp.get("verified_completed"), list) and isinstance(tp.get("remaining"), list)
          and isinstance(tp.get("currently_attempting"), str)
          and all(isinstance(x, str) for x in tp["verified_completed"] + tp["remaining"]))
    if not ok:
        err.append("task_progress: needs verified_completed [str], currently_attempting str, remaining [str]")
        return None
    return {"verified_completed": tp["verified_completed"], "currently_attempting": tp["currently_attempting"],
            "remaining": tp["remaining"]}


CLAIM_RE = re.compile(r"grasp|hold|held|pick|lift|place|put|release|contact|touch", re.I)


def _assessment(d, err):
    """Assessment + the evidence-view rule (coupling spec §12): a verified_completed item that claims contact / grasp /
    lift / place / release is valid only if execution_evidence names a wrist view."""
    a = d.get("assessment")
    if not isinstance(a, dict):
        err.append("assessment: missing")
        a = {}
    out = {"task_progress": _progress(a, err),
           "execution_status": _enum(a, "execution_status", EXEC_STATUS, err, "assessment"),
           "intent_status": _enum(a, "intent_status", INTENT_STATUS, err, "assessment"),
           "confidence": _enum(a, "confidence", CONFIDENCE, err, "assessment")}
    for k in ("current_subgoal", "execution_evidence", "intent_evidence"):
        if not isinstance(a.get(k), str):
            err.append(f"assessment.{k}: not a string")
        out[k] = str(a.get(k, ""))[:400]
    tp = out["task_progress"]
    out["claims"] = [x for x in (tp["verified_completed"] if tp else []) if CLAIM_RE.search(x)]
    if out["claims"] and "wrist" not in out["execution_evidence"].lower():
        err.append("assessment.execution_evidence: a contact / grasp / place claim in verified_completed needs "
                   "evidence from a wrist view (name the view)")
    return out


def is_uncertain(parsed: dict) -> bool:
    """Coupling spec §11: uncertain status or low confidence -> treated as continue (no takeover)."""
    a = parsed["assessment"]
    return a["execution_status"] == "uncertain" or a["intent_status"] == "uncertain" or a["confidence"] == "low"


def _grasp(d, err):
    return {"grasp_state": _enum(d, "grasp_state", ("grasped", "not_grasped", "uncertain"), err, ""),
            "evidence_view": _enum(d, "evidence_view", ("head", "right_wrist", "left_wrist", "multiple"), err, ""),
            "evidence": str(d.get("evidence", ""))[:300], "confidence": _enum(d, "confidence", CONFIDENCE, err, "")}


def _edit(e, err, where="edit"):
    if not isinstance(e, dict):
        err.append(f"{where}: missing")
        return None
    dp = _vec3(e, "delta_position_cm", err, where)
    dr = _vec3(e, "delta_rotation_rad", err, where, required=False)
    if dp is not None and np.linalg.norm(dp) > EDIT_MAX_CM + 1e-9:
        err.append(f"{where}.delta_position_cm: norm exceeds {EDIT_MAX_CM:g} cm")
    if dr is not None and np.linalg.norm(dr) > ROT_MAX_RAD + 1e-9:
        err.append(f"{where}.delta_rotation_rad: norm exceeds {ROT_MAX_RAD} rad")
    return {"delta_position_cm": dp, "delta_rotation_rad": dr, "gripper": _enum(e, "gripper", GRIPPER, err, where)}


def _cmd(d, err):
    out = {"assessment": _assessment(d, err), "decision": _enum(d, "decision", DECISIONS, err, ""),
           "reason": str(d.get("reason", ""))[:400]}
    if out["decision"] == "edit":
        out["edit"] = _edit(d.get("edit"), err)
    return out


def _diff(d, err):
    out = {"assessment": _assessment(d, err), "decision": _enum(d, "decision", ("keep", "revise"), err, "")}
    ev = d.get("evidence")
    if not isinstance(ev, str) or not ev.strip():
        err.append("evidence: required non-empty string")
    out["evidence"] = str(ev or "")[:400]
    if out["decision"] == "revise":
        c = d.get("command")
        if not isinstance(c, dict):
            err.append("command: required for revise")
        else:
            dec = _enum(c, "decision", ("edit", "stop"), err, "command")
            out["command"] = {"decision": dec}
            if dec == "edit":
                out["command"]["edit"] = _edit(c.get("edit"), err, "command.edit")
    return out


def validate(mode: str, text: str, *_, **__):
    """(parsed dict, []) or (None, [errors]). mode: S-cmd | S-diff."""
    err: list = []
    try:
        d = extract_json(text)
    except SchemaError as e:
        return None, [str(e)]
    if mode == "S-cmd":
        out = _cmd(d, err)
    elif mode == "S-diff":
        out = _diff(d, err)
    elif mode == "G":
        out = _grasp(d, err)
    else:
        raise ValueError(mode)
    return (out, []) if not err else (None, err)
