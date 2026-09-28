"""E-OPRATIO8-S1 verdict (prereg_opratio_s1.md): p75 vs p0 pooled over training seeds 0 and 1.
Pairs are (seed, state) / (seed, G row): p75 seed s vs p0 seed s; one paired bootstrap (10,000, seed 0) over the pooled
pairs. L8-X: all 7 sets upper bound <= +2 mm (mean approach 3D). G: each of the 6 subsets not worse -- hit lower bound
> -0.03 (Where2Place > -0.10), label subsets pixel error upper bound <= +3 px. Reported (not judged): L8-X medians and
the 'no descend' rate per arm and seed.
usage: python opratio_s1_compare.py <eval root> <g_eval.jsonl> <x data dir> <out json>"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import opratio_compare as OC  # noqa: E402

SEEDS = (0, 1)
W2P_MARGIN = 0.10
MARGIN = 0.03


def arm_dir(a, s):
    return f"op_p{a}" if s == 0 else f"op_p{a}_s{s}"


def main(root, gpath, xdir, outp):
    grows = OC.jl(gpath)
    gsub = {r["id"]: OC.GSUB[r["gset"]] for r in grows}
    ids = [r["id"] for r in grows]
    X, G, rep = {}, {}, {"arms": {}}
    for a in (0, 75):
        for s in SEEDS:
            d = arm_dir(a, s)
            G[a, s] = {r["id"]: r for r in OC.jl(os.path.join(root, d, "g", "scores.jsonl"))}
            info = {"x": {}, "g": {}}
            for xs in OC.XSETS:
                sc, inf = OC.xset(root, f"{a}" if s == 0 else f"{a}_s{s}", xs, xdir)
                X[a, s, xs] = sc
                e = [r["approach_3d_mm"] for r in sc.values() if r.get("approach_3d_mm") is not None]
                inf.update(approach_mean=round(float(np.mean(e)), 2), approach_median=round(float(np.median(e)), 2))
                info["x"][xs] = inf
            for sub in sorted(set(gsub.values())) + ["ALL"]:
                k = [i for i in ids if sub == "ALL" or gsub[i] == sub]
                info["g"][sub] = {"hit": round(float(np.mean([bool(G[a, s].get(i, {}).get("hit")) for i in k])), 4)}
            rep["arms"][d] = info
    v = {"x": {}, "g": {}}
    ok = True
    for xs in OC.XSETS:
        diffs, n = [], 0
        for s in SEEDS:
            A, B = X[75, s, xs], X[0, s, xs]
            ks = [k for k in A if k in B and A[k].get("approach_3d_mm") is not None and B[k].get("approach_3d_mm") is not None]
            diffs += [A[k]["approach_3d_mm"] - B[k]["approach_3d_mm"] for k in ks]
        ci = OC.boot(diffs)
        v["x"][xs] = {"n_pairs": len(diffs), "diff_mean_mm": round(float(np.mean(diffs)), 2), "diff_ci95_mm": ci,
                      "noninferior": bool(ci[1] <= 2.0)}
        ok &= ci[1] <= 2.0
    for sub in sorted(set(gsub.values())) + ["ALL"]:
        k = [i for i in ids if sub == "ALL" or gsub[i] == sub]
        h = lambda a, s, i: float(bool(G[a, s].get(i, {}).get("hit")))
        hd = [h(75, s, i) - h(0, s, i) for s in SEEDS for i in k]
        d = {"hit_diff": round(float(np.mean(hd)), 4), "hit_ci95": OC.boot(hd)}
        if sub not in ("where2place", "refspatial", "ALL"):
            pd = [G[75, s][i]["px_err"] - G[0, s][i]["px_err"] for s in SEEDS for i in k
                  if G[75, s].get(i, {}).get("px_err") is not None and G[0, s].get(i, {}).get("px_err") is not None]
            d["px_ci95"] = OC.boot(pd)
        if sub != "ALL":
            m = W2P_MARGIN if sub == "where2place" else MARGIN
            d["margin"] = m
            d["worse"] = bool(d["hit_ci95"][0] <= -m or ("px_ci95" in d and d["px_ci95"][1] > 3.0))
            ok &= not d["worse"]
        v["g"][sub] = d
    v["qualified"] = bool(ok)
    rep["p75_vs_p0_pooled"] = v
    rep["pick"] = ({"p": 75, "verdict": "BETTER" if v["g"]["ALL"]["hit_ci95"][0] > 0 else "SAME"} if ok
                   else {"p": 0, "verdict": "NOT_QUALIFIED"})
    json.dump(rep, open(outp, "w"), indent=1)
    print(json.dumps(rep["pick"]))


if __name__ == "__main__":
    main(*sys.argv[1:5])
