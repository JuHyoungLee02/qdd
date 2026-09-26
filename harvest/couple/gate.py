"""Meaning checks of one Astra coupling answer (spec §11, §12, §15; GPT-as-Policy gate_assessment.validate_assessment):
  - claims: kept only from the ACTIVE wrist camera and when not contradicted by the T1 proprio holding value
    (wrist first + proprio cross-check, spec §12); head-only / other-wrist / contradicted claims are logged in notes;
  - task_progress with grasp / lift / place words is trusted only when the active wrist is among the evidence views;
  - edit / stop: stale (answer age > stale_edit_s, canon §86: 15 s; skipped with stale_ok when the canon §91
    reconciliation found the judged world unchanged, plan Task 19) -> continue (assessment kept); uncertain
    execution or intent or confidence low -> continue (spec §11); an edit needs execution failed or intent
    misaligned; edit and stop need evidence text + views; stop needs a wrist placed / released claim (plan ruling 8).
takeover_ok (used by the layer for F1 keep) = a takeover reason, not uncertain, evidence present, not stale."""
from __future__ import annotations

import re

ACTIVE_WRIST = {"right": "cam_wrist_right", "left": "cam_wrist_left"}
PROGRESS_WORDS = re.compile(r"grasp|hold|held|pick|lift|place|put|release|contact|touch", re.I)
_T1_CONTRA = {"grasped": True, "released": False, "placed": False, "not_grasped": False}  # claim valid if holding ==


def gate_answer(a, p, t1: dict, stale_ok: bool = False):
    """stale_ok: the arrival reconciliation (canon §91, reconcile.py) found the world the answer judged unchanged
    (verdict valid-still) -- the age rule is subsumed there, so the stale drop is skipped (plan Task 19)."""
    wrist = ACTIVE_WRIST[p.active_arm]
    keep = []
    for kind, view in a.claims:
        if not view.startswith("cam_wrist"):
            a.notes.append(f"head_only_claim:{kind}")
            continue
        if view != wrist:
            a.notes.append(f"other_wrist_claim:{kind}")
            continue
        h = t1.get("holding_t")
        if kind in _T1_CONTRA and h is not None and bool(h) != _T1_CONTRA[kind]:
            a.notes.append(f"claim_vs_t1:{kind}")
            continue
        keep.append((kind, view))
    a.claims = tuple(keep)
    done = " ".join(a.task_progress.get("verified_completed", []))
    a.progress_trusted = not (PROGRESS_WORDS.search(done) and wrist not in a.evidence_views)
    if not a.progress_trusted:
        a.notes.append("progress_claim_without_wrist")
    uncertain = a.execution == "uncertain" or a.intent == "uncertain" or a.confidence == "low"
    reason = a.execution == "failed" or a.intent == "misaligned"
    has_ev = bool(a.evidence.strip()) and bool(a.evidence_views)
    stale = a.age > p.stale_edit_s + 1e-9 and not stale_ok
    a.takeover_ok = reason and not uncertain and has_ev and not stale
    if a.diff == "keep" and stale:
        a.notes.append("stale_keep")
    gate = "ok"
    if a.command in ("edit", "stop"):
        if stale:
            gate = "stale"
        elif uncertain:
            gate = "uncertain"
        elif a.command == "edit" and not reason:
            gate = "no_takeover_reason"
        elif not has_ev:
            gate = "no_evidence"
        elif a.command == "stop" and not any(k in ("placed", "released") for k, _ in a.claims):
            gate = "stop_without_wrist_claim"
    if gate != "ok":
        a.command, a.edit = "continue", None
    a.gate = gate
    return a
