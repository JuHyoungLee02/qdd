"""L9 robot production gate (user 10-03 02h, L9_PRINCIPLES §6). Read-only.
A robot (per task kind: single-arm, articulated, bimanual) passes when
  (a) scene skips caused by limited arm reach are not failures: skipped rows (skipped.json, no episode) are left out
      of every denominator; they are only counted by reason;
  (b) every definition the robot attempted (>= 1 rendered episode) has >= 1 success AND a success rate >= 10 %;
  (c) the mean of the per-definition success rates is >= 40 %.
usage: python tools/l9/robot_gate9.py <collect root>... [--robot r1pro] [--min-eps 1] [--json out.json]
A collect root is a dir with <split>/<family>/<episode>/meta.json (or skipped.json)."""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

REACH_WORDS = ("reach", "outside its", "standing band", "ik precheck")  # articulated: IK precheck = arm cannot reach


def skip_kind(reason: str) -> str:
    r = (reason or "").lower()
    if any(w in r for w in REACH_WORDS):
        return "reach"
    if "no valid grasp" in r:
        return "no_valid_grasp"
    if "does not fit" in r:
        return "scene_fit"
    if "out of view" in r:
        return "out_of_view"
    return "other"


def evaluate(roots, robot=None, min_eps=1) -> dict:
    eps, succ = Counter(), Counter()
    skips = defaultdict(Counter)
    for root in roots:
        for d in glob.glob(os.path.join(root, "*", "*", "*")):
            m = os.path.join(d, "meta.json")
            if os.path.exists(m):
                try:
                    meta = json.load(open(m))
                except ValueError:
                    continue
                if robot and (meta.get("robot") or "ffw_sg2") != robot:
                    continue
                k = meta.get("task_id") or "?"
                eps[k] += 1
                succ[k] += bool(meta.get("success"))
                continue
            s = os.path.join(d, "skipped.json")
            if os.path.exists(s):
                try:
                    sk = json.load(open(s))
                except ValueError:
                    continue
                row = sk.get("row") or {}
                if robot and (row.get("robot") or "ffw_sg2") != robot:
                    continue
                skips[row.get("def") or "?"][skip_kind(sk.get("reason", ""))] += 1
    defs = {}
    for k in sorted(eps):
        if eps[k] < min_eps:
            continue
        rate = succ[k] / eps[k]
        defs[k] = {"eps": eps[k], "succ": succ[k], "rate": round(rate, 3),
                   "ok": succ[k] >= 1 and rate >= 0.10, "skips": dict(skips.get(k, {}))}
    rates = [v["rate"] for v in defs.values()]
    mean = round(sum(rates) / len(rates), 3) if rates else 0.0
    failing = sorted(k for k, v in defs.items() if not v["ok"])
    sk_total = Counter()
    for c in skips.values():
        sk_total.update(c)
    return {"robot": robot, "defs_attempted": len(defs), "episodes": sum(eps.values()), "successes": sum(succ.values()),
            "pooled_rate": round(sum(succ.values()) / max(1, sum(eps.values())), 3), "mean_def_rate": mean,
            "defs_failing_b": len(failing), "failing_examples": failing[:15], "skips_by_kind": dict(sk_total),
            "pass_b": not failing, "pass_c": mean >= 0.40, "PASS": (not failing) and mean >= 0.40 and bool(defs),
            "defs": defs}


def main():
    a = sys.argv[1:]
    arg = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    vals = {arg(k, None) for k in ("--robot", "--min-eps", "--json")}
    roots = [x for x in a if not x.startswith("--") and x not in vals]
    rep = evaluate(roots, arg("--robot", None), int(arg("--min-eps", "1")))
    out = arg("--json", None)
    if out:
        json.dump(rep, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "defs"}))


if __name__ == "__main__":
    main()
