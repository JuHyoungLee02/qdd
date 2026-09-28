"""E-OPRATIO8 verdict (prereg_opratio.md section 3): each p>0 arm vs p=0.
  L8-X 7 sets: paired snapshot bootstrap (10,000, seed 0) of the mean approach 3D error difference; non-inferior when
    the upper 95 % bound <= +2 mm. Also per arm: the 'no descend' rate = share of descend steps (descend_close /
    lower_open) whose reply asks height "above".
  G: 6 subsets (4 open held-out sources, Where2Place, RefSpatial-Bench pooled); a subset is worse when the hit
    difference lower bound <= -0.03 or (label subsets) the pixel error mean difference upper bound > +3 px.
    An invalid reply counts as a miss. Selection: best G overall hit among qualified arms; BETTER if its G hit
    difference lower bound > 0, else SAME; no qualified arm -> p=0.
usage: python opratio_compare.py <eval root> <g_eval.jsonl> <x data dir> <out json>"""
import json
import os
import re
import sys

import numpy as np

ARMS = (0, 25, 50, 75)
XSETS = ("dev", "ood_h", "ood_d", "ood_o", "ood_s", "ood_t", "ood_hl")
GSUB = {"behavior": "behavior", "molmobot_franka": "molmobot_franka", "molmobot_rby1": "molmobot_rby1", "rb2": "rb2",
        "where2place": "where2place", "refspatial_location": "refspatial", "refspatial_placement": "refspatial",
        "refspatial_unseen": "refspatial"}
DESCEND = ("descend_close", "lower_open")


def boot(v, n=10000, seed=0):
    v = np.asarray(v, float)
    m = v[np.random.default_rng(seed).integers(0, len(v), (n, len(v)))].mean(1)
    return [round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]


def jl(p):
    return [json.loads(x) for x in open(p, encoding="utf-8")]


def height_of(text):
    m = re.search(r'"height"\s*:\s*"(\w+)"', text or "")
    return m.group(1) if m else None


def xset(root, arm, s, xdir):
    d = os.path.join(root, f"op_p{arm}", f"x_{s}_d-min_clean")
    sc = {r["id"]: r for r in jl(os.path.join(d, "scores.jsonl"))}
    rep = {r["id"]: r["text"] for r in jl(os.path.join(d, "replies.jsonl")) if not r.get("error")}
    steps = {r["id"]: r["step"] for r in jl(os.path.join(xdir, f"x_{s}_d-min_clean.jsonl"))}
    dn = [k for k, st in steps.items() if st in DESCEND]
    above = sum(height_of(rep.get(k)) == "above" for k in dn)
    return sc, {"n_descend": len(dn), "no_descend": above, "no_descend_rate": round(above / max(len(dn), 1), 4),
                "valid": round(sum(r["valid"] for r in sc.values()) / max(len(sc), 1), 4)}


def gscores(root, arm):
    return {r["id"]: r for r in jl(os.path.join(root, f"op_p{arm}", "g", "scores.jsonl"))}


def main(root, gpath, xdir, outp):
    grows = jl(gpath)
    gsub = {r["id"]: GSUB[r["gset"]] for r in grows}
    ids = [r["id"] for r in grows]
    res = {"arms": {}, "vs_p0": {}}
    X = {a: {} for a in ARMS}
    G = {a: gscores(root, a) for a in ARMS}
    for a in ARMS:
        info = {"x": {}, "g": {}}
        for s in XSETS:
            X[a][s], info["x"][s] = xset(root, a, s, xdir)
            e = [r["approach_3d_mm"] for r in X[a][s].values() if r.get("approach_3d_mm") is not None]
            info["x"][s].update(approach_mean=round(float(np.mean(e)), 2), approach_median=round(float(np.median(e)), 2))
        for sub in sorted(set(gsub.values())) + ["ALL"]:
            k = [i for i in ids if sub == "ALL" or gsub[i] == sub]
            hit = [bool(G[a].get(i, {}).get("hit")) for i in k]
            pe = [G[a][i]["px_err"] for i in k if G[a].get(i, {}).get("px_err") is not None]
            info["g"][sub] = {"n": len(k), "hit": round(float(np.mean(hit)), 4),
                              "valid": round(float(np.mean([bool(G[a].get(i, {}).get("valid")) for i in k])), 4),
                              "px_median": round(float(np.median(pe)), 1) if pe else None}
        res["arms"][f"p{a}"] = info
    qualified = []
    for a in ARMS[1:]:
        v = {"x": {}, "g": {}}
        ok = True
        for s in XSETS:
            ks = [k for k in X[a][s] if k in X[0][s] and X[a][s][k].get("approach_3d_mm") is not None
                  and X[0][s][k].get("approach_3d_mm") is not None]
            ci = boot([X[a][s][k]["approach_3d_mm"] - X[0][s][k]["approach_3d_mm"] for k in ks])
            ni = ci[1] <= 2.0
            ok &= ni
            v["x"][s] = {"n_pairs": len(ks), "diff_ci95_mm": ci, "noninferior": ni}
        for sub in sorted(set(gsub.values())) + ["ALL"]:
            k = [i for i in ids if sub == "ALL" or gsub[i] == sub]
            h = lambda A, i: float(bool(G[A].get(i, {}).get("hit")))
            hci = boot([h(a, i) - h(0, i) for i in k])
            d = {"hit_diff": round(float(np.mean([h(a, i) - h(0, i) for i in k])), 4), "hit_ci95": hci}
            pk = [i for i in k if G[a].get(i, {}).get("px_err") is not None and G[0].get(i, {}).get("px_err") is not None]
            if pk and sub not in ("where2place", "refspatial", "ALL"):
                d["px_ci95"] = boot([G[a][i]["px_err"] - G[0][i]["px_err"] for i in pk])
            if sub != "ALL":
                d["worse"] = bool(hci[0] <= -0.03 or ("px_ci95" in d and d["px_ci95"][1] > 3.0))
                ok &= not d["worse"]
            v["g"][sub] = d
        v["qualified"] = bool(ok)
        res["vs_p0"][f"p{a}"] = v
        if ok:
            qualified.append(a)
    if qualified:
        best = max(qualified, key=lambda a: res["arms"][f"p{a}"]["g"]["ALL"]["hit"])
        lo = res["vs_p0"][f"p{best}"]["g"]["ALL"]["hit_ci95"][0]
        res["pick"] = {"p": best, "verdict": "BETTER" if lo > 0 else "SAME"}
    else:
        res["pick"] = {"p": 0, "verdict": "NO_QUALIFIED_ARM"}
    json.dump(res, open(outp, "w"), indent=1)
    print(json.dumps(res["pick"]))


if __name__ == "__main__":
    main(*sys.argv[1:5])
