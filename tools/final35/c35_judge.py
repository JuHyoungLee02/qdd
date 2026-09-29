"""E-C35 judge (docs/stage3/prereg_c35.md): c35 (seeds 0, 1; best validation epoch each) vs f35_d (09-28, one seed).
A/A margins from the c35 seed pair (35B, same training file) - ni_judge rule (user-log 186):
  L8-X dev / OOD-H / OOD-O + new OOD-O 58: median and >20 mm failure rate (tools/teach_pt/ni_judge.py);
  G (6 subsets + ALL): hit rate and point pixel error (open held-out subsets), as tools/teach_pt/poolv_compare.py.
The single f35_d run is paired with both c35 seeds (Y dirs = [f35_d, f35_d]).
usage: python c35_judge.py <c35 s0 eval dir> <c35 s1 eval dir> <f35_d eval dir> <g_eval.jsonl> <out json>"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "teach_pt"))
import ni_judge as NJ  # noqa: E402
import poolv_compare as PC  # noqa: E402

NJ.XSETS = ("dev", "ood_h", "ood_o", "ood_o58")


def main(s0, s1, base, gpath, outp):
    NJ.aa(outp + ".aa_x.json", [s0, s1])
    X = NJ.judge(outp + ".aa_x.json", outp + ".judge_x.json", [s0, s1], [base, base])
    grows = PC.jl(gpath)
    sub = {r["id"]: PC.GSUB[r["gset"]] for r in grows}
    S = {k: PC.gs(os.path.dirname(d), os.path.basename(d)) for k, d in (("s0", s0), ("s1", s1), ("b", base))}
    res = {"x": X, "g": {}, "worse": list(X["worse_sets"])}
    for sb in sorted(set(sub.values())) + ["ALL"]:
        ids = [r["id"] for r in grows if sb == "ALL" or sub[r["id"]] == sb]
        info = {"n": len(ids)}
        for what in ("hit", "px") if sb in PC.PX_SUBS else ("hit",):
            sgn = -1.0 if what == "hit" else 1.0  # positive = c35 worse
            margin = float(np.percentile(np.abs(PC.boot_mean_diff(PC.gvec(S["s1"], ids, what) - PC.gvec(S["s0"], ids, what))), 95))
            d = np.concatenate([sgn * (PC.gvec(S[k], ids, what) - PC.gvec(S["b"], ids, what)) for k in ("s0", "s1")])
            bt = PC.boot_mean_diff(d)
            lo, hi = float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))
            mc = float(np.nanmean(np.concatenate([PC.gvec(S[k], ids, what) for k in ("s0", "s1")])))
            info[what] = {"f35_d": round(float(np.nanmean(PC.gvec(S["b"], ids, what))), 4), "c35": round(mc, 4),
                          "c35_worse_ci95": [round(lo, 4), round(hi, 4)], "aa_margin": round(margin, 4),
                          "noninferior": hi <= margin}
            if hi > margin:
                res["worse"].append(f"g_{sb}_{what}")
        res["g"][sb] = info
    res["verdict"] = "NONINFERIOR" if not res["worse"] else "WORSE"
    json.dump(res, open(outp, "w"), indent=1)
    print(json.dumps({"verdict": res["verdict"], "worse": res["worse"]}))


if __name__ == "__main__":
    main(*sys.argv[1:6])
