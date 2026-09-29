"""E-POOLV8 judge (docs/stage3/prereg_poolv.md): NEW pool vs OLD pool, two seeds each.
L8-X dev / OOD-O: ni_judge (A/A margins from the seed pairs of each arm, median + >20 mm failure rate).
G (6 subsets + ALL): hit-rate difference (OLD - NEW) and point pixel error difference (NEW - OLD, open held-out
subsets only) over the pooled (seed, row) pairs, paired bootstrap 10,000 (seed 0); A/A margin = 95th percentile of the
pooled |bootstrap difference| of the two A/A pairs; non-inferior when the upper 95 % bound <= margin.
usage: python poolv_compare.py <eval root> <g_eval.jsonl> <out json>"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ni_judge as NJ  # noqa: E402

NJ.XSETS = ("dev", "ood_o")
GSUB = {"behavior": "behavior", "molmobot_franka": "molmobot_franka", "molmobot_rby1": "molmobot_rby1", "rb2": "rb2",
        "where2place": "where2place", "refspatial_location": "refspatial", "refspatial_placement": "refspatial",
        "refspatial_unseen": "refspatial"}
PX_SUBS = ("behavior", "molmobot_franka", "molmobot_rby1", "rb2")
N_BOOT = 10000


def jl(p):
    return [json.loads(x) for x in open(p, encoding="utf-8")]


def gs(root, arm):
    return {r["id"]: r for r in jl(os.path.join(root, arm, "g", "scores.jsonl"))}


def gvec(S, ids, what):
    if what == "hit":
        return np.array([float(bool(S.get(i, {}).get("hit"))) for i in ids])
    return np.array([S[i]["px_err"] if S.get(i, {}).get("px_err") is not None else np.nan for i in ids])


def boot_mean_diff(d, seed=0):
    d = d[~np.isnan(d)]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (N_BOOT, len(d)))
    return d[idx].mean(1)


def main(root, gpath, outp):
    old, new = ["pv_old_s0", "pv_old_s1"], ["pv_new_s0", "pv_new_s1"]
    ed = lambda a: os.path.join(root, a)
    M = NJ.aa(outp + ".aa_x.json", [ed(old[0]), ed(old[1]), ed(new[0]), ed(new[1])])
    X = NJ.judge(outp + ".aa_x.json", outp + ".judge_x.json", [ed(a) for a in new], [ed(a) for a in old])
    grows = jl(gpath)
    sub = {r["id"]: GSUB[r["gset"]] for r in grows}
    ids_all = [r["id"] for r in grows]
    S = {a: gs(root, a) for a in old + new}
    res = {"x": X, "g": {}, "worse": list(X["worse_sets"])}
    for sb in sorted(set(sub.values())) + ["ALL"]:
        ids = [i for i in ids_all if sb == "ALL" or sub[i] == sb]
        info = {"n": len(ids)}
        for what in ("hit", "px") if sb in PX_SUBS else ("hit",):
            sgn = -1.0 if what == "hit" else 1.0  # positive = NEW worse
            aa = []
            for a0, a1 in ((old[0], old[1]), (new[0], new[1])):
                aa.append(np.abs(boot_mean_diff(gvec(S[a1], ids, what) - gvec(S[a0], ids, what))))
            margin = float(np.percentile(np.concatenate(aa), 95))
            d = np.concatenate([sgn * (gvec(S[n], ids, what) - gvec(S[o], ids, what)) for n, o in zip(new, old)])
            bt = boot_mean_diff(d)
            lo, hi = float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))
            mean = lambda arms: float(np.nanmean(np.concatenate([gvec(S[a], ids, what) for a in arms])))
            info[what] = {"old": round(mean(old), 4), "new": round(mean(new), 4),
                          "new_worse_ci95": [round(lo, 4), round(hi, 4)], "aa_margin": round(margin, 4),
                          "noninferior": hi <= margin}
            if hi > margin:
                res["worse"].append(f"g_{sb}_{what}")
        res["g"][sb] = info
    res["verdict"] = "NONINFERIOR" if not res["worse"] else "WORSE"
    json.dump(res, open(outp, "w"), indent=1)
    print(json.dumps({"verdict": res["verdict"], "worse": res["worse"]}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
