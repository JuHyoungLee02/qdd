"""L9 robot production gate (user 10-03 02h, L9_PRINCIPLES §6). Read-only.
A robot (per task kind: single-arm, articulated, bimanual) passes when
  (a) scene skips caused by limited arm reach are not failures: skipped rows (skipped.json, no episode) are left out
      of every denominator; they are only counted by reason;
  (b) every definition the robot attempted (>= 1 rendered episode) has >= 1 success AND a success rate >= 10 %;
  (c) the mean of the per-definition success rates is >= 40 %.
(b) is judged only on definitions with >= 5 attempted episodes (user 10-03 02h); a definition with fewer is
"pending" (fill it to 5, then judge). verdict: FAIL (a judged definition fails (b), or (c) fails with nothing
pending) / PENDING (definitions still below 5) / PASS (all judged, (b) and (c) hold); pending_need = episodes to add.
usage: python tools/l9/robot_gate9.py <collect root>... [--robot r1pro] [--min-eps 1] [--json out.json] [--exclude a,b]
--exclude: definitions still experimental for every robot (main 10-03 02h, L9_PRINCIPLES §6: robots are judged only
on definitions in production for the passing robots); default EXPERIMENTAL_ALL below.
A collect root is a dir with <split>/<family>/<episode>/meta.json (or skipped.json)."""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

JUDGE_MIN_EPS = 5  # user 10-03 02h: (b) is judged only on definitions with >= 5 attempted episodes; fewer = "pending"
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


EXPERIMENTAL_ALL = ("drawer_put_close", "drawer_take_close")  # experimental for every robot (+ AIW far push defs)


def evaluate(roots, robot=None, min_eps=1, exclude=EXPERIMENTAL_ALL) -> dict:
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
    excluded = sorted(k for k in eps if k in set(exclude))
    for k in sorted(eps):
        if eps[k] < min_eps or k in set(exclude):
            continue
        rate = succ[k] / eps[k]
        judged = eps[k] >= JUDGE_MIN_EPS
        defs[k] = {"eps": eps[k], "succ": succ[k], "rate": round(rate, 3), "judged": judged,
                   "ok": (succ[k] >= 1 and rate >= 0.10) if judged else None, "skips": dict(skips.get(k, {}))}
    rates = [v["rate"] for v in defs.values()]
    mean = round(sum(rates) / len(rates), 3) if rates else 0.0
    failing = sorted(k for k, v in defs.items() if v["ok"] is False)
    pending = sorted(k for k, v in defs.items() if not v["judged"])
    sk_total = Counter()
    for c in skips.values():
        sk_total.update(c)
    verdict = "FAIL" if failing or (defs and mean < 0.40 and not pending) else ("PENDING" if pending or not defs
                                                                             else "PASS")
    return {"robot": robot, "defs_attempted": len(defs), "episodes": sum(eps.values()), "successes": sum(succ.values()),
            "pooled_rate": round(sum(succ.values()) / max(1, sum(eps.values())), 3), "mean_def_rate": mean,
            "defs_failing_b": len(failing), "failing_examples": failing[:15],
            "defs_pending": len(pending), "pending_need": {k: JUDGE_MIN_EPS - defs[k]["eps"] for k in pending},
            "excluded_experimental": excluded, "skips_by_kind": dict(sk_total), "pass_b": not failing, "pass_c": mean >= 0.40,
            "PASS": verdict == "PASS", "verdict": verdict, "defs": defs}


def main():
    a = sys.argv[1:]
    arg = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    vals = {arg(k, None) for k in ("--robot", "--min-eps", "--json", "--exclude")}
    roots = [x for x in a if not x.startswith("--") and x not in vals]
    ex = arg("--exclude", None)
    rep = evaluate(roots, arg("--robot", None), int(arg("--min-eps", "1")),
                   tuple(x for x in ex.split(",") if x) if ex is not None else EXPERIMENTAL_ALL)
    out = arg("--json", None)
    if out:
        json.dump(rep, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "defs"}))


if __name__ == "__main__":
    main()
