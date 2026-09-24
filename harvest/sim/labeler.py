"""Outcome-based labeler (E §2A.3, D4 F5): options tied for the best rollout score are all correct."""


def best_set(scores: dict, tol: float = 1e-6) -> set:
    top = max(scores.values())
    return {k for k, v in scores.items() if top - v <= tol}
