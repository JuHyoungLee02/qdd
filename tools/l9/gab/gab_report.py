"""L9v2-general integrated A/B report + pre-registered verdict (docs/stage3/results/l9v2_general_ab.md). Read-only.
usage: python -m tools.l9.gab.gab_report <ab dir> [--json out.json] [--aba module:function]
--aba: a function f(meta: dict, ep_dir: str) -> bool|None (True = the episode has a place round trip A-B-A; None =
       not measurable) supplied by the place-oscillation owner; without it the ABA rows read "n/a"."""
import importlib
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import robot_gate9 as g  # noqa: E402

GATE = 0.04
ROBOTS = ("ffw_sg2", "franka_mast", "r1pro", "g1")
MARGIN_ROBOT = 0.10  # per robot: B pass rate >= A - 10 pp
MARGIN_POOL = 0.05  # all robots pooled: B >= A - 5 pp
ABA_TOL = 0.02  # B ABA share <= A + 2 pp


def scan(root, aba=None):
    eps, skips = defaultdict(dict), defaultdict(dict)
    for d, _, files in os.walk(root):
        if "meta.json" in files:
            try:
                m = json.load(open(os.path.join(d, "meta.json")))
            except ValueError:
                continue
            m["_aba"] = aba(m, d) if aba else None
            eps[m.get("robot") or "ffw_sg2"][int(m["seed"])] = m
        elif "skipped.json" in files:
            try:
                s = json.load(open(os.path.join(d, "skipped.json")))
            except ValueError:
                continue
            row = s.get("row") or {}
            skips[row.get("robot") or "ffw_sg2"][int(row.get("seed", -1))] = g.skip_kind(s.get("reason", ""))
    return eps, skips


def ok(m):
    return bool(m.get("success")) and float(m.get("max_dq_rad") or 0.0) <= GATE


def arm_stats(eps, skips):
    ms = list(eps.values())
    fam = defaultdict(lambda: [0, 0])
    for m in ms:
        f = fam[str(m.get("task_family"))]
        f[0] += 1
        f[1] += ok(m)
    ab = [m["_aba"] for m in ms if m.get("_aba") is not None]
    succ = [m for m in ms if m.get("success")]
    return {"episodes": len(ms), "skips": dict(Counter(skips.values())), "success": len(succ),
            "pass": sum(ok(m) for m in ms), "rate": round(sum(ok(m) for m in ms) / max(1, len(ms)), 3),
            "dq_over": sum(1 for m in ms if float(m.get("max_dq_rad") or 0.0) > GATE),
            "spec": dict(Counter(str(m.get("spec_version")) for m in ms)),
            "family": {k: f"{v[1]}/{v[0]}" for k, v in sorted(fam.items())},
            "aba_share": round(sum(ab) / len(ab), 3) if ab else None, "aba_n": len(ab),
            "profile": g.profile(succ)}


def main():
    a = sys.argv[1:]
    ab = a[0]
    aba = None
    if "--aba" in a:
        mod, fn = a[a.index("--aba") + 1].split(":")
        aba = getattr(importlib.import_module(mod), fn)
    A = scan(os.path.join(ab, "A", "collect"), aba)
    B = scan(os.path.join(ab, "B", "collect"), aba)
    res, pool = {}, {"A": [0, 0], "B": [0, 0]}
    for robot in ROBOTS:
        ea, eb = A[0].get(robot, {}), B[0].get(robot, {})
        if not ea and not eb:
            continue
        sa, sb = arm_stats(ea, A[1].get(robot, {})), arm_stats(eb, B[1].get(robot, {}))
        common = sorted(set(ea) & set(eb))
        pair = Counter((ok(ea[s]), ok(eb[s])) for s in common)
        div = g.diversity_check(sb["profile"], sa["profile"], robot) if sa["profile"]["n"] and sb["profile"]["n"] else None
        lost_fam = sorted(f for f, v in sa["family"].items() if int(v.split("/")[0]) >= 2
                          and sb["family"].get(f, "0/0").split("/")[0] == "0")
        r = {"A": sa, "B": sb, "paired_seeds": len(common),
             "paired": {"both": pair[(True, True)], "A_only": pair[(True, False)], "B_only": pair[(False, True)],
                        "neither": pair[(False, False)]},
             "diversity_B_vs_A": div, "families_lost": lost_fam}
        r["succ_ok"] = sb["rate"] >= sa["rate"] - MARGIN_ROBOT and not lost_fam
        # left/right is reference only (user 10-03: balanced at build time, not in raw production)
        r["div_ok"] = None if div is None else not [k for k in div["narrower"] if k != "arms"]
        r["dq_ok"] = sb["dq_over"] <= sa["dq_over"] + 1
        r["aba_ok"] = None if sa["aba_share"] is None or sb["aba_share"] is None else sb["aba_share"] <= sa["aba_share"] + ABA_TOL
        r["n_ok"] = sa["episodes"] >= 20 and sb["episodes"] >= 20
        r["PASS"] = all(v is not False for k, v in r.items() if k.endswith("_ok"))
        res[robot] = r
        for k, s in (("A", sa), ("B", sb)):
            pool[k][0] += s["episodes"]
            pool[k][1] += s["pass"]
    ra, rb = (round(pool[k][1] / max(1, pool[k][0]), 3) for k in ("A", "B"))
    verdict = {"pooled_A": ra, "pooled_B": rb, "pool_ok": rb >= ra - MARGIN_POOL,
               "robots_pass": {k: v["PASS"] for k, v in res.items()}}
    verdict["PASS"] = verdict["pool_ok"] and len(res) == 4 and all(v["PASS"] for v in res.values())
    out = {"verdict": verdict, "robots": res}
    if "--json" in a:
        json.dump(out, open(a[a.index("--json") + 1], "w"), indent=1)
    for robot, r in res.items():
        print(f"{robot:12s} A {r['A']['pass']}/{r['A']['episodes']} ({r['A']['rate']})  B {r['B']['pass']}/{r['B']['episodes']} "
              f"({r['B']['rate']})  paired {r['paired']}  skipsA {r['A']['skips']} skipsB {r['B']['skips']}  "
              f"abaA {r['A']['aba_share']} abaB {r['B']['aba_share']}  div {None if not r['diversity_B_vs_A'] else r['diversity_B_vs_A']['narrower']}"
              f"  lost {r['families_lost']}  PASS {r['PASS']}")
    print("VERDICT", json.dumps(verdict))


if __name__ == "__main__":
    main()
