"""L9 v2 task diversity metrics for the gate (main 10-02 02h; owner additions: place height / pose / approach,
post-grasp steps). Works on an allocation (alloc_v2.json from plan.py v2), a plan (plan_v2.json rows) or collected
episodes (meta.json files, successes only by default).

Reported: definitions, families, per-family definitions, episode distribution per definition (min / median / max,
share under 60, normalised entropy), robot x family coverage, instruction variety (template capacity for plans,
unique instruction strings for metas), planned or measured place pose / place approach / place height / scene
constraint / instructed approach distributions, steps per episode and post-grasp calls (= place / grasp calls after the
first grasp: 2 x steps - 1, + 2 per recovery), recovery share, held-out share.
usage: python tools/l9/task_diversity.py (--alloc A.json | --plan P.json | --metas ROOT [--all]) [--out R.json]"""
import argparse
import glob
import json
import math
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.l9 import task9v2 as V2  # noqa: E402

MIN_PER_DEF = 60


def _entropy(c: Counter) -> float:
    n = sum(c.values())
    if n <= 0 or len(c) <= 1:
        return 0.0
    h = -sum(v / n * math.log(v / n) for v in c.values() if v > 0)
    return round(h / math.log(len(c)), 4)


def _dist(c: Counter) -> dict:
    n = sum(c.values()) or 1
    return {str(k): {"n": v, "share": round(v / n, 4)} for k, v in sorted(c.items(), key=lambda x: -x[1])}


def _per_def(c: Counter) -> dict:
    v = sorted(c.values())
    if not v:
        return {"total": 0}
    return {"total": sum(v), "per_def_min": v[0], "per_def_median": v[len(v) // 2], "per_def_max": v[-1],
            "under_60": sum(x < MIN_PER_DEF for x in v), "entropy_norm": _entropy(c)}


def _planned(weights: Counter) -> dict:
    """Episode-weighted planned features from the definitions' static profiles."""
    pose, appr, height, cons, steps, post = Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    rec = 0
    for k, n in weights.items():
        p = V2.def_profile(V2.DEFS_V2[k])
        for x in p["place_poses"]:
            pose[x] += n
        for x in p["place_approach"]:
            appr[x] += n
        for x in p["place_height"]:
            height[x] += n
        for x in p["constraints"] or ["none"]:
            cons[x] += n
        steps[p["n_steps"]] += n
        post[p["post_grasp_calls"]] += n
        rec += n * p["recovery"]
    tot = sum(weights.values()) or 1
    return {"place_pose_planned": _dist(pose), "approach_planned": _dist(appr), "height_planned": _dist(height),
            "constraints_planned": _dist(cons), "n_steps": _dist(steps), "post_grasp_steps": _dist(post),
            "recovery_share": round(rec / tot, 4), "multi_step_share": round(sum(v for s, v in steps.items() if s >= 2) / tot, 4)}


def from_alloc(alloc: dict, holdout=()) -> dict:
    per, rob_fam = Counter(), defaultdict(set)
    fams = Counter()
    for k, v in alloc.items():
        d = V2.DEFS_V2[k]
        per[k] = sum(v.values())
        fams[d.family] += per[k]
        for r, n in v.items():
            if n > 0:
                rob_fam[r].add(d.family)
    rep = {"source": "alloc", "n_defs": len(alloc), "n_families": len(fams),
           "defs_per_family": dict(Counter(V2.DEFS_V2[k].family for k in alloc)),
           "episodes": _per_def(per), "family_episodes": _dist(fams), "family_entropy_norm": _entropy(fams),
           "robot_family_cover": {r: len(f) for r, f in sorted(rob_fam.items())},
           "robot_episodes": dict(sum((Counter(v) for v in alloc.values()), Counter())),
           "templates_total": sum(len(V2.DEFS_V2[k].templates) for k in alloc),
           "template_capacity": sum(len(V2.DEFS_V2[k].templates) for k in alloc) * V2.N_WRAPPERS *
           (1 + sum(len(t) for t in V2.APPROACH_TEXT.values())),
           "instructed_share_planned": V2.INSTRUCTED_SHARE,
           "holdout": {"defs": sorted(holdout), "episodes": sum(per[k] for k in holdout)}}
    rep.update(_planned(per))
    nat = V2.natural_expected(alloc)  # natural_v1 grasp family / part expected from the catalog (class-balanced)
    rep["natural_expected"] = {"overall": {k: round(v, 4) for k, v in nat["overall"].items()}, "parts": nat["parts"],
                               "per_def": nat["per_def"]}
    return rep


def from_plan(rows: list) -> dict:
    per = Counter(r["def"] for r in rows)
    rep = from_alloc({k: dict(Counter(r["robot"] for r in rows if r["def"] == k)) for k in per},
                     holdout={r["def"] for r in rows if r.get("split") == "holdout"})
    rep["source"] = "plan (rows, not successes)"
    rep["arms"] = dict(Counter((r.get("robot"), r["arm"]) for r in rows).most_common()) if rows else {}
    rep["arms"] = {f"{a}/{b}": n for (a, b), n in rep["arms"].items()}
    rep["env_families"] = _dist(Counter(r["family"] for r in rows))
    rep["layouts"] = len({(r["family"], r["rule"]) for r in rows})
    rep["splits"] = dict(Counter(r.get("split", "train") for r in rows))
    return rep


def from_metas(root: str, success_only: bool = True) -> dict:
    per, fams, robots = Counter(), Counter(), Counter()
    instr, pose, appr, cons, band, steps, post, inst = set(), Counter(), Counter(), Counter(), Counter(), Counter(), \
        Counter(), Counter()
    rec = n = 0
    for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
        try:
            x = json.load(open(m))
        except (OSError, ValueError):
            continue
        if success_only and not x.get("success"):
            continue
        n += 1
        k = x.get("task_id")
        per[k] += 1
        fams[x.get("task_family")] += 1
        robots[x.get("robot") or "ffw_sg2"] += 1
        if x.get("instruction"):
            instr.add(x["instruction"])
        si = x.get("step_info") or []
        ns = int(x.get("n_steps") or len(si) or 1)
        steps[ns] += 1
        r = sum(1 for s in si if s.get("recovery"))
        rec += bool(r)
        post[2 * ns - 1 + 2 * r] += 1
        for s in si:
            pose[(s.get("place_pose") or {}).get("kind")] += 1
            appr[s.get("place_approach")] += 1
            cons[s.get("constraint") or "none"] += 1
            band[(s.get("place_height") or {}).get("band")] += 1
        inst[((x.get("instr_meta") or {}).get("approach")) or "none"] += 1
    return {"source": "metas", "episodes_n": n, "n_defs": len(per), "n_families": len(fams),
            "episodes": _per_def(per), "family_entropy_norm": _entropy(fams), "robots": dict(robots),
            "unique_instructions": len(instr), "place_pose": _dist(pose), "place_approach": _dist(appr),
            "constraints": _dist(cons), "place_height": _dist(band), "n_steps": _dist(steps),
            "post_grasp_steps": _dist(post), "instructed_approach": _dist(inst), "recovery_share": round(rec / max(n, 1), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alloc")
    ap.add_argument("--plan")
    ap.add_argument("--metas")
    ap.add_argument("--all", action="store_true", help="metas: count failed episodes too")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.alloc:
        j = json.load(open(a.alloc))
        rep = from_alloc(j["alloc"], j.get("holdout", ()))
    elif a.plan:
        rep = from_plan(json.load(open(a.plan)))
    elif a.metas:
        rep = from_metas(a.metas, not a.all)
    else:
        raise SystemExit(__doc__)
    s = json.dumps(rep, indent=1, ensure_ascii=False)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(s)
    print(s)


if __name__ == "__main__":
    main()
