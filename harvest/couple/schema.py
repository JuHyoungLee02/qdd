"""Astra coupling answer schema (astra-couple@v1): general control only (spec revision, user-log 83) with the
GPT-as-Policy gate vocabulary (gate_assessment.py). parse_answer checks structure only and raises SchemaError with
every problem found; the meaning checks (age, uncertainty, takeover reason, wrist evidence) are gate.py.

version "v2" (astra-couple@v2, plan 2026-09-26 Task 18, harvest/couple/prompt_v2.py): the same common part plus a
required segment plan {now, do, next} (names only, serialize.SEGMENTS / SEGMENT_ACTIONS, canon §90), a required
edit.valid_until (next_answer | segment_end), the stated edit limit 0.04 m with the parser tolerance EDIT_MAX_M 0.05 m
(P62), and an F1 keep's accompanying edit ignored with a note (prompt health F9) instead of a schema error. v1
parsing is unchanged (recorded v1 runs stay reproducible)."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field

import numpy as np

from ..serialize import SEGMENT_ACTIONS, SEGMENTS

SCHEMA_ID = "astra-couple@v1"
SCHEMA_IDS = {"v1": SCHEMA_ID, "v2": "astra-couple@v2"}
VALID_UNTIL = ("next_answer", "segment_end")
EXEC_STATUS = ("not_started", "progressing", "failed", "uncertain", "recovered")
INTENT_STATUS = ("aligned", "misaligned", "uncertain")
CONFIDENCE = ("low", "medium", "high")
COMMANDS = ("continue", "edit", "stop")
DIFFS = ("keep", "revise")
GRIPPER = ("keep", "open", "close")
INFO_REQUESTS = ("none", "slow_down")
CLAIM_KINDS = ("grasp_ready", "grasped", "not_grasped", "released", "placed", "contact")
EDIT_MAX_M, ROT_MAX_RAD = 0.05, 0.35
TOL = 1e-9


class SchemaError(ValueError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


@dataclass
class Edit:
    dp: np.ndarray
    dr: np.ndarray
    gripper: str

    def vec6(self) -> np.ndarray:
        return np.r_[self.dp, self.dr].astype(float)

    def to_json(self) -> dict:
        return {"delta_position_m": [round(float(v), 4) for v in self.dp],
                "delta_rotation_rad": [round(float(v), 4) for v in self.dr], "gripper": self.gripper}


@dataclass
class AstraAnswer:
    request_no: int
    t_state: float
    t_deliver: float
    diff: str | None
    command: str
    edit: Edit | None
    execution: str
    intent: str
    confidence: str
    evidence: str
    evidence_views: tuple
    claims: tuple
    task_progress: dict
    info_request: str = "none"
    gate: str = "raw"
    takeover_ok: bool = False
    progress_trusted: bool = True
    notes: list = field(default_factory=list)
    segment: dict | None = None  # v2: Astra's segment plan {now, do, next} as answered (raw, logged)
    valid_until: str | None = None  # v2: the edit's validity (next_answer | segment_end)

    @property
    def age(self) -> float:
        return self.t_deliver - self.t_state


def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise SchemaError(["no JSON object in the answer"])
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise SchemaError([f"JSON: {e.msg}"]) from None
    if not isinstance(d, dict):
        raise SchemaError(["the answer is not a JSON object"])
    return d


def _vec3(x, lim: float, name: str, err: list):
    ok = isinstance(x, list) and len(x) == 3 and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in x)
    if not ok:
        err.append(f"{name}: 3 finite numbers")
        return None
    v = np.asarray(x, float)
    if float(np.linalg.norm(v)) > lim + TOL:
        err.append(f"{name}: norm {float(np.linalg.norm(v)):.4f} > {lim}")
        return None
    return v


def _progress_ok(tp) -> bool:
    return (isinstance(tp, dict)
            and all(isinstance(tp.get(k), list) and all(isinstance(s, str) and s.strip() for s in tp[k])
                    for k in ("verified_completed", "remaining"))
            and isinstance(tp.get("currently_attempting"), str) and bool(tp["currently_attempting"].strip()))


def parse_answer(text: str, mode: str, sent_cameras, request_no: int, t_state: float,
                 t_deliver: float, version: str = "v1") -> AstraAnswer:
    d = extract_json(text)
    sent = tuple(sent_cameras)
    err, notes = [], []
    a = d.get("assessment")
    if not isinstance(a, dict):
        raise SchemaError(["assessment: object required"])
    tp = a.get("task_progress")
    if not _progress_ok(tp):
        err.append("assessment.task_progress: verified_completed[], currently_attempting, remaining[]")
    for k, allowed in (("execution", EXEC_STATUS), ("intent", INTENT_STATUS), ("confidence", CONFIDENCE)):
        if a.get(k) not in allowed:
            err.append(f"assessment.{k}: one of {allowed}")
    ev = a.get("evidence", "")
    if not isinstance(ev, str):
        err.append("assessment.evidence: string")
        ev = ""
    views = a.get("evidence_views", [])
    if not (isinstance(views, list) and all(v in sent for v in views)):
        err.append(f"assessment.evidence_views: subset of the cameras sent {list(sent)}")
        views = []
    claims = []
    raw_claims = a.get("claims", [])
    for c in raw_claims if isinstance(raw_claims, list) else [None]:
        if not (isinstance(c, dict) and c.get("kind") in CLAIM_KINDS and c.get("view") in sent):
            err.append(f"assessment.claims: {{kind in {CLAIM_KINDS}, view in the cameras sent}}")
            break
        claims.append((c["kind"], c["view"]))
    diff = None
    if mode == "F1":
        diff = d.get("diff")
        if diff not in DIFFS:
            err.append(f"diff: one of {DIFFS}")
    cmd = "continue" if diff == "keep" else d.get("command")
    if cmd not in COMMANDS:
        err.append(f"command: one of {COMMANDS}")
    v2 = version == "v2"
    if v2 and diff == "keep" and d.get("edit") not in (None, {}):
        d = {k: v for k, v in d.items() if k != "edit"}  # F9: keep confirms the command being applied
        notes.append("keep_edit_ignored")
    edit, vu, seg = None, None, None
    if v2:
        s = d.get("segment")
        if (isinstance(s, dict) and s.get("now") in SEGMENTS and s.get("do") in SEGMENT_ACTIONS
                and s.get("next") in SEGMENTS):
            seg = {k: s[k] for k in ("now", "do", "next")}
        else:
            err.append(f"segment: {{now, next in {SEGMENTS}, do in {SEGMENT_ACTIONS}}}")
    if cmd == "edit":
        e = d.get("edit")
        if not isinstance(e, dict):
            err.append("edit: object required with command edit")
        else:
            dp = _vec3(e.get("delta_position_m"), EDIT_MAX_M, "edit.delta_position_m", err)
            dr = _vec3(e.get("delta_rotation_rad", [0.0, 0.0, 0.0]), ROT_MAX_RAD, "edit.delta_rotation_rad", err)
            g = e.get("gripper", "keep")
            if v2:
                vu = e.get("valid_until")
                if vu not in VALID_UNTIL:
                    err.append(f"edit.valid_until: one of {VALID_UNTIL}")
            if g not in GRIPPER:
                err.append(f"edit.gripper: one of {GRIPPER}")
            elif dp is not None and dr is not None:
                edit = Edit(dp, dr, g)
    elif d.get("edit") not in (None, {}):
        err.append("edit: only with command edit")
    info = d.get("info_request", "none")
    if info not in INFO_REQUESTS:
        err.append(f"info_request: one of {INFO_REQUESTS}")
    if err:
        raise SchemaError(err)
    return AstraAnswer(request_no=request_no, t_state=float(t_state), t_deliver=float(t_deliver), diff=diff,
                       command=cmd, edit=edit, execution=a["execution"], intent=a["intent"],
                       confidence=a["confidence"], evidence=ev, evidence_views=tuple(views), claims=tuple(claims),
                       task_progress=tp, info_request=info, notes=notes, segment=seg, valid_until=vu)
