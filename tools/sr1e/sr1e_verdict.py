"""E-SR1e verdict (docs/stage3/prereg_sr1e.md §4, fixed before the main runs; not edited after results).

  python tools/sr1e/sr1e_verdict.py --c0 C0_S1.jsonl C0_S2.jsonl --arm A A_S1.jsonl A_S2.jsonl \
      [--arm D D_S1.jsonl D_S2.jsonl] --n 1799 --out verdict.json [--boot 10000]

Per arm: the E-SR1d rule unchanged (tools/sr1d/sr1d_verdict.py imported, not modified; mode far): far A_xy >= 0.80 and
each seed >= 0.75, near non-inferiority N1-N5, whole-range (i)-(iv) against C0 = motion_s1 / motion_s2 evaluated in the
same E-SR1e evaluation phase; every metric = the mean of the two seeds. Verdict per arm: ADOPT (grade FULL / XY),
NEAR_BLEED, NOT_ADOPTED, NOT_REACHED.
Arms are given in order of simplicity (first = simplest). Overall:
  no arm ADOPT                  -> NOT_REACHED if every arm fails 'far', else NONE_ADOPTED (arm verdicts reported)
  exactly one arm ADOPT         -> ADOPT_<arm>
  several ADOPT                 -> the simplest ADOPT arm, unless a more complex ADOPT arm has far A_xy higher by
                                   >= +0.03 with paired-bootstrap 2.5 % > 0 (then the highest such arm)
L1 (contrastive decision guidance on the E-SR1d C1 checkpoints, tools/sr1e/cdg_eval.py; --cdg-base = w 1 files,
--cdg W S1 S2 per w > 1): per w the E-SR1d far / N1-N5 / (i)-(iii) rule against C0, and in place of (iv): latency p95
<= w1 + 40 ms; far true-decision chunk MSE <= w1 x 1.05; forced far chunk |disp| p95 <= recorded far chunk p95 x 1.2
(each seed). Smallest passing w -> CDG_ADOPT_w<w>, none -> CDG_NONE.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sr1d_verdict", os.path.join(_HERE, "..", "sr1d", "sr1d_verdict.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

GAIN_MIN = 0.03
EPS = 1e-12


def arm_result(c0_runs, c0_lat, runs, lat, boot):
    per = {"c0_s1": V.summarize(c0_runs[0], "far"), "c0_s2": V.summarize(c0_runs[1], "far"),
           "c1_s1": V.summarize(runs[0], "far"), "c1_s2": V.summarize(runs[1], "far")}
    for k, v in zip(("c0_s1", "c0_s2", "c1_s1", "c1_s2"), (*c0_lat, *lat)):
        per[k]["latency_p95_ms"] = v
    avg = {arm: V.average([per[f"{arm}_s1"], per[f"{arm}_s2"]]) for arm in ("c0", "c1")}
    seeds_far = [per["c1_s1"]["primary"]["a_xy"], per["c1_s2"]["primary"]["a_xy"]]
    rule = V.check(avg["c1"], avg["c0"], seeds_far)
    prim0 = [[x for x in V.groups(r, "far")["primary"]] for r in c0_runs]
    prim1 = [[x for x in V.groups(r, "far")["primary"]] for r in runs]
    d, lo, hi = V.paired_diff(prim0, prim1, boot)
    return {"rule": rule, "avg": avg, "per_seed": per, "ci95_primary": V.V0.boot_ci(prim1, boot, 0),
            "minus_c0_primary": {"diff": d, "ci95": [lo, hi]}}, prim1


def overall(names, res, prims, boot):
    ok = [n for n in names if res[n]["rule"]["verdict"] == "ADOPT"]
    if not ok:
        if all(res[n]["rule"]["verdict"] == "NOT_REACHED" for n in names):
            return {"verdict": "NOT_REACHED", "arm": None, "pairs": {}}
        return {"verdict": "NONE_ADOPTED", "arm": None, "pairs": {}}
    pick, pairs = ok[0], {}
    for n in ok[1:]:
        d, lo, hi = V.paired_diff(prims[pick], prims[n], boot)
        pairs[f"{n}-{pick}"] = {"diff": d, "ci95": [lo, hi]}
        if d >= GAIN_MIN - EPS and lo > 0:
            pick = n
    return {"verdict": f"ADOPT_{pick}", "arm": pick, "grade": res[pick]["rule"]["grade"], "pairs": pairs}


CDG_MSE_X, CDG_MAG_X, CDG_LAT_MS = 1.05, 1.2, 40.0


def far_mag_p95(snaps):
    """(p95 |forced chunk| over far xy pairs d != label, p95 |recorded chunk| over far snapshots), metres."""
    import numpy as np
    f = [s for s in snaps if s["stratum"] == "far"]
    forced = [float(np.linalg.norm(s["c"][f"xy:{d}"][:3])) for s in f for d in V.V0.DIR_XY8
              if d != s["labels"]["dir_xy"]]
    rec = [float(np.linalg.norm(s["disp_gt"])) for s in f]
    return float(np.percentile(forced, 95)), float(np.percentile(rec, 95))


def cdg_check(c0_avg, base_avg, avg, seeds_far, mags):
    """L1 rule for one w: E-SR1d far / N1-N5 / (i)-(iii) against C0, latency <= w1 + 40 ms, far true MSE <= w1 x 1.05,
    forced chunk p95 <= recorded p95 x 1.2 (each seed)."""
    r = V.check(avg, c0_avg, seeds_far)
    checks = {k: v for k, v in r["checks"].items() if k != "iv"}
    checks["iv_cdg"] = avg["latency_p95_ms"] <= base_avg["latency_p95_ms"] + CDG_LAT_MS + EPS
    checks["far_mse"] = avg["primary"]["mse_true"] <= base_avg["primary"]["mse_true"] * CDG_MSE_X + EPS
    checks["mag"] = all(fm <= rm * CDG_MAG_X + EPS for fm, rm in mags)
    fails = [k for k, ok in checks.items() if not ok]
    return {"pass": not fails, "fails": fails, "checks": checks, "a_xy_far": avg["primary"]["a_xy"],
            "a_xy_far_seeds": seeds_far, "mag_p95": mags}


def cdg_main(a):
    """--cdg-base W1_S1 W1_S2 --cdg W S1 S2 ...: the L1 part (registered §4.2); smallest passing w adopted."""
    def load2(paths):
        out = []
        for p in paths:
            snaps, summ = V.load(p, a.n)
            out.append((snaps, [V.snap_stats(s) for s in snaps], (summ.get("latency_ms") or {}).get("p95")))
        return out

    def avg_of(runs):
        per = []
        for _, st, lat in runs:
            p = V.summarize(st, "far")
            p["latency_p95_ms"] = lat
            per.append(p)
        return V.average(per), per
    c0, base = load2(a.c0), load2(a.cdg_base)
    c0_avg, _ = avg_of(c0)
    base_avg, _ = avg_of(base)
    res = {"base": {"a_xy_far": base_avg["primary"]["a_xy"], "latency_p95_ms": base_avg["latency_p95_ms"],
                    "far_mse_true": base_avg["primary"]["mse_true"]}, "w": {}}
    adopted = None
    for w, s1, s2 in sorted(a.cdg, key=lambda x: float(x[0])):
        runs = load2([s1, s2])
        avg, per = avg_of(runs)
        seeds = [p["primary"]["a_xy"] for p in per]
        mags = [far_mag_p95(sn) for sn, _, _ in runs]
        g2 = max(abs(x - y) for (sn, _, _), (bn, _, _) in zip(runs, base) for s, b in zip(sn, bn)
                 for x, y in zip(s["c"]["pred"][:3], b["c"]["pred"][:3]))
        r = cdg_check(c0_avg, base_avg, avg, seeds, mags)
        r["g2_pred_max_diff_m"] = g2
        r["avg"] = avg
        res["w"][w] = r
        if adopted is None and r["pass"]:
            adopted = w
    res["verdict"] = f"CDG_ADOPT_w{adopted}" if adopted else "CDG_NONE"
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(json.dumps({"verdict": res["verdict"], **{w: {k: r[k] for k in ("pass", "fails", "a_xy_far", "a_xy_far_seeds",
                                                                          "g2_pred_max_diff_m")}
                                                    for w, r in res["w"].items()}}, default=float), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdg-base", nargs=2, default=None, help="L1: w = 1 evaluations (C1 s1 / s2)")
    ap.add_argument("--cdg", nargs=3, action="append", default=None, metavar=("W", "S1", "S2"))
    ap.add_argument("--c0", nargs=2, required=True)
    ap.add_argument("--arm", nargs=3, action="append", default=None, metavar=("NAME", "S1", "S2"))
    ap.add_argument("--n", type=int, default=1799)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cdg_base:
        if not a.cdg:
            raise SystemExit("--cdg-base needs --cdg")
        cdg_main(a)
        return
    if not a.arm:
        raise SystemExit("--arm required")
    files, stats, lat = {}, {}, {}
    for name, paths in [("c0", a.c0)] + [(x[0], x[1:]) for x in a.arm]:
        stats[name], lat[name] = [], []
        for i, p in enumerate(paths):
            snaps, summ = V.load(p, a.n)
            stats[name].append([V.snap_stats(s) for s in snaps])
            lat[name].append((summ.get("latency_ms") or {}).get("p95"))
            files[f"{name}_s{i + 1}"] = {"path": p, "keys_sha": summ.get("keys_sha"), "latency_ms": summ.get("latency_ms")}
    ids = [x["id"] for x in stats["c0"][0]]
    if any([x["id"] for x in r] != ids for v in stats.values() for r in v):
        raise SystemExit("the runs are not on the same snapshots in the same order")
    if any(v is None for vs in lat.values() for v in vs):
        raise SystemExit("latency missing (--latency)")
    names = [x[0] for x in a.arm]
    if len(set(names)) != len(names) or "c0" in names:
        raise SystemExit("arm names must be distinct and not 'c0'")
    res, prims = {}, {}
    for n in names:
        res[n], prims[n] = arm_result(stats["c0"], lat["c0"], stats[n], lat[n], a.boot)
    out = {"files": files, "arms": names, "overall": overall(names, res, prims, a.boot), "per_arm": res,
           "ci95_primary_c0": V.V0.boot_ci([[x for x in V.groups(r, "far")["primary"]] for r in stats["c0"]], a.boot, 0)}
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    print(json.dumps({"overall": out["overall"], **{n: {"rule": res[n]["rule"], "minus_c0": res[n]["minus_c0_primary"]}
                                                     for n in names}}, default=float), flush=True)


if __name__ == "__main__":
    main()
