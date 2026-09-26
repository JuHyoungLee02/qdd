"""E-CONF decision-confidence LOGGING hook: conf-base@v1 (canon §95, dated implementation bullet; source
`docs/stage3/results/conf.md` §5, judgment NONE -- the score is kept as a "why this choice" record only, never a
gate: §95 (a) stream-priority display and (b) conservative-mode stay OFF, plan 2026-09-26 Task 22).

conf_from_answers() is a PURE, cheap (no forward pass) function of a decide() call's per-question
{p_chosen, p_second} -- exactly `harvest.runtime.fused_model.answers_from` / `models.py` ModelResult.answers
(the option-softmax top-1 / top-2 probabilities already computed for the vote). It never reads back into any
control path; callers only attach its result to a decision log / sidecar row.

conf-base@v1 record (conf.md §5): {"ver", "min_margin", "argmin_q", "per_q": {q: {"top1", "top2", "margin"}},
"joint"} where min_margin = min_q ln(p_chosen(q) / p_second(q)) and joint = -sum_q ln(p_chosen(q)).

Edge cases (conf.md §5 "질문별 1·2등 로그확률 차"; JSON has no inf/nan, so non-finite margins are `null` + a
signed `margin_inf` flag on that question, and a non-finite joint is `null` + `joint_inf: true`):
  - p_second == 0 (a single-option question, or a mock selector's p_chosen=1.0 / p_second=0.0, models.py:120):
    the ratio is +inf (maximally confident) -> margin=null, margin_inf=+1.
  - p_chosen == 0: the ratio is -inf regardless of p_second (checked first: 0/0 is the same "no evidence on the
    chosen option" case as 0/x) -> margin=null, margin_inf=-1. This dominates the argmin (the worst case sorts
    first), matching "min" literally: a -inf margin is smaller than any finite or +inf one.
  - NONE_ESCALATE options (models.py `NE`): not excluded -- they carry ordinary p_chosen/p_second like any other
    choice and are scored the same way (conf.md §5 does not exclude them).
  - argmin_q tie-break: deterministic by question order (the `answers` dict's own iteration order, i.e. the
    DecCall question order) -- ties keep the first question seen.
  - Modular back-ends without confidence fields (a future selector that does not return p_chosen/p_second):
    conf_from_answers returns None, so nothing is recorded (the caller just skips attaching the block).
"""
from __future__ import annotations

import math

VER = "conf-base@v1"


def _margin(p_chosen: float, p_second: float):
    """ln(p_chosen / p_second) for one question, or (None, sign) for the two non-finite cases above."""
    if p_chosen <= 0.0:
        return None, -1
    if p_second <= 0.0:
        return None, 1
    return math.log(p_chosen / p_second), 0


def _sort_key(sign: int, margin):
    """Ascending key so min() over questions picks -inf (sign<0) first, then finite by value, then +inf (sign>0)
    last -- literally the smallest ln(p_chosen/p_second), non-finite values included."""
    if sign < 0:
        return (-1, 0.0)
    if sign > 0:
        return (1, 0.0)
    return (0, margin)


def conf_from_answers(answers: dict) -> dict | None:
    """{"ver", "min_margin", "argmin_q", "per_q", "joint", ["joint_inf"]} (conf-base@v1, conf.md §5) from a decide()
    ModelResult.answers dict (question -> {..., "p_chosen", "p_second", ...}), or None if `answers` is empty or any
    question is missing p_chosen / p_second (record only if the selector returns those fields)."""
    if not answers:
        return None
    per_q, best_q, best_key = {}, None, None
    joint_terms, joint_inf = [], False
    for q, a in answers.items():
        p1, p2 = a.get("p_chosen"), a.get("p_second")
        if p1 is None or p2 is None:
            return None
        p1, p2 = float(p1), float(p2)
        margin, sign = _margin(p1, p2)
        entry = {"top1": p1, "top2": p2, "margin": margin}
        if sign:
            entry["margin_inf"] = sign
        per_q[q] = entry
        key = _sort_key(sign, margin if margin is not None else 0.0)
        if best_key is None or key < best_key:
            best_key, best_q = key, q
        if p1 <= 0.0:
            joint_inf = True
        else:
            joint_terms.append(-math.log(p1))
    conf = {"ver": VER, "min_margin": per_q[best_q]["margin"], "argmin_q": best_q, "per_q": per_q,
            "joint": None if joint_inf else sum(joint_terms)}
    if joint_inf:
        conf["joint_inf"] = True
    return conf
