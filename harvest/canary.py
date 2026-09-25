"""Daily canary (E §1.8, canon §28): decision-model answer drift vs baseline day; Astra plan-signature drift.

Written for Jev; Jev is unusable (user-log 46), so the decision model is now Jev-L / the fused model (canon §44,
§58) -- harvest.eval.canary builds the sets and calls canary_compare."""
import hashlib
import json
import re
from collections import Counter

from .analysis.stats import N_BOOT, cluster_bootstrap_ci, holm_ci


def plan_signature(plan: dict) -> str:
    """Stage skill sequence + decision point ids + object roles (canon §28); wording is ignored."""
    sig = {"skills": [(s.get("skill"), s.get("obj"), s.get("target")) for s in plan.get("stages", [])],
           "dps": sorted(plan.get("decision_points", [])), "roles": plan.get("roles", {})}
    return hashlib.sha256(json.dumps(sig, sort_keys=True).encode()).hexdigest()[:16]


def _split_key(key: str) -> tuple[str, str]:
    """"<snapshot>|<question>" -> (snapshot, question); a key without "|" is its own snapshot, question "all"."""
    return tuple(key.rsplit("|", 1)) if "|" in key else (key, "all")


def episode_of_key(key: str) -> str:
    """Episode cluster of a canary key: the snapshot id "<kind>_ep<seed>_k<k>" (eval.canary build_set) without its
    "_k<k>"; any other snapshot id is its own cluster."""
    return re.sub(r"_k\d+$", "", _split_key(key)[0])


def canary_compare(base: dict, today: dict, floor: float, n_boot=N_BOOT) -> dict:
    """base/today: "<snapshot>|<question>" -> list of answers (option_key). Canon §28 (:264) / E §1.8: drift suspect
    when the mismatch vs the baseline mode is significantly above the day's floor ("하한 > 0, Holm"): per question
    the episode-cluster bootstrap CI (E §1.7 "스냅샷의 에피소드" clusters) of (mismatch - floor), Holm step-down over
    the questions (stats.holm_ci); drift_suspect = some question rejected with lower > 0. The floor is the day's
    pooled test-retest mismatch, taken as given (canon §73)."""
    per_q = {}
    allv = []
    for key, answers in today.items():
        mode = Counter(base[key]).most_common(1)[0][0]
        vals = [float(a != mode) for a in answers]
        allv += vals
        q = _split_key(key)[1]
        per_q.setdefault(q, {}).setdefault(episode_of_key(key), []).extend(vals)
    mean = sum(allv) / max(1, len(allv))
    h = holm_ci(lambda q, level: cluster_bootstrap_ci(per_q[q], lambda xs: sum(xs) / len(xs) - floor, n=n_boot,
                                                      level=level), sorted(per_q))
    pq = {q: {"mismatch": sum(sum(v) for v in per_q[q].values()) / sum(len(v) for v in per_q[q].values()),
              "reject": bool(r["reject"]), "lo": r["lo"], "hi": r["hi"], "level": r["level"]} for q, r in h.items()}
    drift = any(v["reject"] and v["lo"] > 0 for v in pq.values())
    return {"mismatch": mean, "lower_minus_floor": max(v["lo"] for v in pq.values()) if pq else None,
            "per_question": pq, "drift_suspect": bool(drift), "n_boot": n_boot, "boot_seed": 0,
            "boot_unit": "episode (snapshot id without _k<k>), per question; Holm over questions",
            "n_clusters": len({c for v in per_q.values() for c in v}), "alpha": 0.05}
