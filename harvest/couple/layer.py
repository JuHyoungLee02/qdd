"""Astra-layer agreement (spec §5 hysteresis, §11 weights): consecutive gated answers in request order.
  edit, no candidate            -> apply the new edit at single_weight (50 %), it becomes the candidate
  edit, same as the candidate   -> confirm: 100 % (the first proposal's vector, plan ruling 7)
  edit, > flip_deg from the applied one -> flip: the offset goes back to 0, the new edit becomes a candidate at 0 %
  continue (not keep)           -> the candidate expires (a one-answer spike is ignored for confirmation, logged)
  F1 keep                       -> confirms the candidate only when the keep answer has a takeover reason
  stop twice in a row (F1: stop then keep) -> stop_confirmed (a logged claim, never a physical stop, canon §4).
Segment plan (astra-couple@v2, plan 2026-09-26 Task 18, canon §90 caution), independent of the edit agreement:
  same plan as the agreed one   -> plan_same (a pending different candidate expires)
  a new plan, no / other cand.  -> plan_candidate (logged, not applied)
  the candidate again           -> plan_agreed (two consecutive answers)
  ... but authority a == 0 at delivery and `do` differs from the agreed plan's -> plan_frozen (held, logged; the
      candidate stays, so the next agreeing answer once a > 0 applies it); now / next update when `do` is unchanged.
  v1 answers carry no plan (plan None)."""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import numpy as np


def _ang(a, b) -> float:
    c = float(np.dot(a, b)) / (float(np.linalg.norm(a)) * float(np.linalg.norm(b)))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def _same_part(x, y, small: float, deg: float) -> bool:
    sx, sy = float(np.linalg.norm(x)) < small, float(np.linalg.norm(y)) < small
    if sx or sy:
        return sx and sy
    return _ang(x, y) <= deg + 1e-9


def same_edit(a, b, p) -> bool:
    return (a.gripper == b.gripper and _same_part(a.dp, b.dp, p.small_edit_m, p.same_dir_deg)
            and _same_part(a.dr, b.dr, p.small_rot_rad, p.same_dir_deg))


def _part_flipped(x, y, small: float, deg: float) -> bool:
    return (float(np.linalg.norm(x)) >= small and float(np.linalg.norm(y)) >= small
            and _ang(x, y) > deg + 1e-9)


def flipped(a, b, p) -> bool:
    return (_part_flipped(a.dp, b.dp, p.small_edit_m, p.flip_deg)
            or _part_flipped(a.dr, b.dr, p.small_rot_rad, p.flip_deg))


@dataclass
class LayerResult:
    action: str
    key: int | None = None
    weight: float = 0.0
    edit: object = None
    plan: str | None = None  # the segment-plan action of the same answer (None: no plan in the answer, v1)


class AstraLayer:
    def __init__(self, p):
        self.p = p
        self.pending = None  # (key, Edit) applied at single weight, waiting for the next answer
        self.confirmed = None  # (key, Edit)
        self.stop_pending = False
        self.progress = None
        self.plan, self.plan_cand = None, None  # agreed segment plan / candidate (dicts {now, do, next})
        self.counts = Counter()

    def _res(self, action, key=None, weight=0.0, edit=None) -> LayerResult:
        self.counts[action] += 1
        return LayerResult(action, key, weight, edit)

    def _confirm(self) -> LayerResult:
        key, e = self.pending
        self.pending, self.confirmed = None, (key, e)
        return self._res("confirm", key, 1.0, e)

    def on_plan(self, seg, authority: float = 1.0) -> str | None:
        if seg is None:
            return None
        if seg == self.plan:
            self.plan_cand, act = None, "plan_same"
        elif seg != self.plan_cand:
            self.plan_cand, act = dict(seg), "plan_candidate"
        elif authority <= 0.0 and self.plan is not None and seg["do"] != self.plan["do"]:
            act = "plan_frozen"
        else:
            self.plan, self.plan_cand, act = dict(seg), None, "plan_agreed"
        self.counts[act] += 1
        return act

    def on_answer(self, a, authority: float = 1.0) -> LayerResult:
        """authority: the driver's current a at delivery (canon §84 supplement 8), used by the plan freeze only."""
        res = self._on_answer(a)
        res.plan = self.on_plan(getattr(a, "segment", None), authority)
        return res

    def _on_answer(self, a) -> LayerResult:
        self.counts["answers"] += 1
        if a.progress_trusted:
            self.progress = a.task_progress
        if a.diff == "keep":
            if self.stop_pending:
                self.stop_pending = False
                return self._res("stop_confirmed")
            if self.pending is not None and a.takeover_ok:
                return self._confirm()
            self.pending = None
            return self._res("none")
        if a.command == "stop":
            self.pending = None
            if self.stop_pending:
                self.stop_pending = False
                return self._res("stop_confirmed")
            self.stop_pending = True
            return self._res("stop_claim")
        self.stop_pending = False
        if a.command != "edit":
            self.pending, self.confirmed = None, None
            return self._res("none")
        if self.pending is not None and same_edit(self.pending[1], a.edit, self.p):
            return self._confirm()
        ref = self.pending or self.confirmed
        if ref is not None and flipped(ref[1], a.edit, self.p):
            self.pending, self.confirmed = (a.request_no, a.edit), None
            return self._res("flip", a.request_no, 0.0, a.edit)
        self.pending = (a.request_no, a.edit)
        return self._res("apply", a.request_no, self.p.single_weight, a.edit)

    def flow_last(self) -> dict:
        seg = {} if self.plan is None else {"segment": dict(self.plan)}  # the agreed plan (v2), absent before
        for state, cur in (("unconfirmed", self.pending), ("confirmed", self.confirmed)):
            if cur is not None:
                return {"command": "edit", "edit": cur[1].to_json(), "request_no": cur[0], "state": state, **seg}
        return {"command": "continue", **seg}
