"""E-VIEW8 verdict (prereg_view8.md section 3): arm X vs its predecessor Y, pooled over training seeds 0 and 1.
Pairs are (seed, state) / (seed, G row); one paired bootstrap (10,000, seed 0) over the pooled pairs.
  worse-free: L8-X all 7 sets mean approach 3D upper bound <= +2 mm; G 6 subsets hit lower bound > -0.03
    (Where2Place > -0.10), label subsets pixel error upper bound <= +3 px.
  better: G overall hit lower bound > 0, or the outside benchmarks (RefSpatial + Where2Place pooled) lower bound > 0.
  ADOPT = worse-free and better; SAME = worse-free only (not adopted: no gain); REJECT = something worse.
Reported (not judged): per arm and seed, L8-X means / medians / 'no descend' rate, G subset hits.
usage: python view8_compare.py <eval root> <g_eval.jsonl> <x data dir> <X> <Y> <out json>
  (eval dirs: <eval root>/<arm>_s<seed>/{g, x_<set>_d-min_clean})"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import opratio_compare as OC  # noqa: E402

SEEDS = (0, 1)
OUTSIDE = ("where2place", "refspatial")


def load_arm(root, arm, s, xdir):
    d = os.path.join(root, f"{arm}_s{s}")
    g = {r["id"]: r for r in OC.jl(os.path.join(d, "g", "scores.jsonl"))}
    x, info = {}, {}
    for xs in OC.XSETS:
        xd = os.path.join(d, f"x_{xs}_d-min_clean")
        sc = {r["id"]: r for r in OC.jl(os.path.join(xd, "scores.jsonl"))}
        rep = {r["id"]: r["text"] for r in OC.jl(os.path.join(xd, "replies.jsonl")) if not r.get("error")}
        steps = {r["id"]: r["step"] for r in OC.jl(os.path.join(xdir, f"x_{xs}_d-min_clean.jsonl"))}
        dn = [k for k, st in steps.items() if st in OC.DESCEND]
        above = sum(OC.height_of(rep.get(k)) == "above" for k in dn)
        e = [r["approach_3d_mm"] for r in sc.values() if r.get("approach_3d_mm") is not None]
        x[xs] = sc
        info[xs] = {"approach_mean": round(float(np.mean(e)), 2), "approach_median": round(float(np.median(e)), 2),
                    "no_descend_rate": round(above / max(len(dn), 1), 4), "n_descend": len(dn),
                    "valid": round(sum(r["valid"] for r in sc.values()) / max(len(sc), 1), 4)}
    return g, x, info


def main(root, gpath, xdir, X, Y, outp):
    grows = OC.jl(gpath)
    gsub = {r["id"]: OC.GSUB[r["gset"]] for r in grows}
    ids = [r["id"] for r in grows]
    subs = sorted(set(gsub.values()))
    A = {(a, s): load_arm(root, a, s, xdir) for a in (X, Y) for s in SEEDS}
    rep = {"x": X, "y": Y, "arms": {}}
    for (a, s), (g, _, info) in A.items():
        rep["arms"][f"{a}_s{s}"] = {"x": info, "g": {
            sub: round(float(np.mean([bool(g.get(i, {}).get("hit")) for i in ids if sub == "ALL" or gsub[i] == sub])), 4)
            for sub in subs + ["ALL"]}}
    v, worse = {"x": {}, "g": {}}, False
    for xs in OC.XSETS:
        diffs = []
        for s in SEEDS:
            P, Q = A[X, s][1][xs], A[Y, s][1][xs]
            diffs += [P[k]["approach_3d_mm"] - Q[k]["approach_3d_mm"] for k in P if k in Q
                      and P[k].get("approach_3d_mm") is not None and Q[k].get("approach_3d_mm") is not None]
        ci = OC.boot(diffs)
        v["x"][xs] = {"n_pairs": len(diffs), "diff_mean_mm": round(float(np.mean(diffs)), 2), "diff_ci95_mm": ci,
                      "noninferior": bool(ci[1] <= 2.0)}
        worse |= ci[1] > 2.0
    for sub in subs + ["OUTSIDE", "ALL"]:
        k = [i for i in ids if sub == "ALL" or gsub[i] == sub or (sub == "OUTSIDE" and gsub[i] in OUTSIDE)]
        h = lambda a, s, i: float(bool(A[a, s][0].get(i, {}).get("hit")))
        hd = [h(X, s, i) - h(Y, s, i) for s in SEEDS for i in k]
        d = {"n": len(hd), "hit_diff": round(float(np.mean(hd)), 4), "hit_ci95": OC.boot(hd)}
        if sub in subs and sub not in OUTSIDE:
            pd = [A[X, s][0][i]["px_err"] - A[Y, s][0][i]["px_err"] for s in SEEDS for i in k
                  if A[X, s][0].get(i, {}).get("px_err") is not None and A[Y, s][0].get(i, {}).get("px_err") is not None]
            d["px_ci95"] = OC.boot(pd)
        if sub in subs:
            m = 0.10 if sub == "where2place" else 0.03
            d["worse"] = bool(d["hit_ci95"][0] <= -m or ("px_ci95" in d and d["px_ci95"][1] > 3.0))
            worse |= d["worse"]
        v["g"][sub] = d
    better = v["g"]["ALL"]["hit_ci95"][0] > 0 or v["g"]["OUTSIDE"]["hit_ci95"][0] > 0
    v["verdict"] = "REJECT" if worse else ("ADOPT" if better else "SAME")
    rep["compare"] = v
    json.dump(rep, open(outp, "w"), indent=1)
    print(json.dumps({"x": X, "y": Y, "verdict": v["verdict"]}))


if __name__ == "__main__":
    main(*sys.argv[1:7])
