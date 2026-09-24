"""Oracle scripted planner, DEV perturbations and success predicate (E §1.4)."""
from ..config import CFG

SUCCESS_KEYS = ("on(o3,o5)", "holding(o3)", "upright(o3)")


def _success_now(p: dict) -> bool:
    return p.get("on(o3,o5)") is True and p.get("holding(o3)") is False and p.get("upright(o3)") is True


def success_from_history(hist) -> bool:
    """hist: [(sim_time, predicates)] ascending. True iff the success predicate holds ≥ success_hold_s continuously.
    unknown (None) never counts as satisfied."""
    start = None
    for t, p in hist:
        if _success_now(p):
            start = t if start is None else start
            if t - start >= CFG.success_hold_s - 1e-9:
                return True
        else:
            start = None
    return False
