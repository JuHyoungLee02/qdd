"""Daily canary (E §1.8, canon §28): decision-model answer drift vs baseline day; Astra plan-signature drift.

Written for Jev; Jev is unusable (user-log 46), so the decision model is now Jev-L / the fused model (canon §44,
§58) -- harvest.eval.canary builds the sets and calls canary_compare."""
import hashlib
import json
from collections import Counter

from .analysis.stats import N_BOOT, cluster_bootstrap_ci


def plan_signature(plan: dict) -> str:
    """Stage skill sequence + decision point ids + object roles (canon §28); wording is ignored."""
    sig = {"skills": [(s.get("skill"), s.get("obj"), s.get("target")) for s in plan.get("stages", [])],
           "dps": sorted(plan.get("decision_points", [])), "roles": plan.get("roles", {})}
    return hashlib.sha256(json.dumps(sig, sort_keys=True).encode()).hexdigest()[:16]


def canary_compare(base: dict, today: dict, floor: float, n_boot=N_BOOT) -> dict:
    """base/today: question -> list of answers (option_key). Drift = mismatch vs baseline mode > 2×floor
    and bootstrap lower bound of (mismatch − floor) > 0."""
    per_q = {}
    for q, answers in today.items():
        mode = Counter(base[q]).most_common(1)[0][0]
        per_q[q] = [float(a != mode) for a in answers]
    allv = [v for vs in per_q.values() for v in vs]
    mean = sum(allv) / max(1, len(allv))
    lo, _ = cluster_bootstrap_ci(per_q, lambda xs: sum(xs) / len(xs) - floor, n=n_boot)
    return {"mismatch": mean, "lower_minus_floor": lo, "drift_suspect": bool(mean > 2 * floor and lo > 0),
            "n_boot": n_boot, "boot_seed": 0, "boot_unit": "snapshot|question key"}
