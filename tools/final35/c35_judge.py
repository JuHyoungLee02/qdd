"""E-C35 judge (docs/stage3/prereg_c35.md, change 2 — two arms). A/A margins from arm b seeds 0 / 1 (35B, same file),
ni_judge rule (user-log 186):
  L8-X dev / OOD-H / OOD-O + new OOD-O 58: median and >20 mm failure rate (tools/teach_pt/ni_judge.py);
  G (6 subsets + ALL): hit rate and point pixel error (open held-out subsets), as tools/teach_pt/poolv_compare.py.
Comparisons: b vs f35_d, a vs f35_d, a vs b (seed 0 pair). A single run on one side is paired with each run on the other.
usage: python c35_judge.py <eval root> <g_eval.jsonl> <out dir>
  eval root holds best_b_s0, best_b_s1, best_a_s0, f35_d (each with x_<set>_d-min_clean/ and g/)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "teach_pt"))
import ni_judge as NJ  # noqa: E402
import poolv_compare as PC  # noqa: E402

NJ.XSETS = ("dev", "ood_h", "ood_o", "ood_o58")


def gmargins(root, grows, sub):
    S0, S1 = PC.gs(root, "best_b_s0"), PC.gs(root, "best_b_s1")
    m = {}
    for sb in sorted(set(sub.values())) + ["ALL"]:
        ids = [r["id"] for r in grows if sb == "ALL" or sub[r["id"]] == sb]
        for what in ("hit", "px") if sb in PC.PX_SUBS else ("hit",):
            d = PC.gvec(S1, ids, what) - PC.gvec(S0, ids, what)
            m[(sb, what)] = float(np.percentile(np.abs(PC.boot_mean_diff(d)), 95))
    return m


def compare(root, xs, ys, grows, sub, gm, aa_path, outp):
    """X (candidate) vs Y (reference); lists of run names under root, paired element-wise."""
    X = NJ.judge(aa_path, outp + ".judge_x.json", [os.path.join(root, a) for a in xs], [os.path.join(root, a) for a in ys])
    S = {a: PC.gs(root, a) for a in set(xs) | set(ys)}
    res = {"x_runs": xs, "y_runs": ys, "x": X, "g": {}, "worse": list(X["worse_sets"])}
    for sb in sorted(set(sub.values())) + ["ALL"]:
        ids = [r["id"] for r in grows if sb == "ALL" or sub[r["id"]] == sb]
        info = {"n": len(ids)}
        for what in ("hit", "px") if sb in PC.PX_SUBS else ("hit",):
            sgn = -1.0 if what == "hit" else 1.0  # positive = X worse
            d = np.concatenate([sgn * (PC.gvec(S[x], ids, what) - PC.gvec(S[y], ids, what)) for x, y in zip(xs, ys)])
            bt = PC.boot_mean_diff(d)
            lo, hi = float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))
            mean = lambda runs: round(float(np.nanmean(np.concatenate([PC.gvec(S[a], ids, what) for a in runs]))), 4)
            info[what] = {"y": mean(ys), "x": mean(xs), "x_worse_ci95": [round(lo, 4), round(hi, 4)],
                          "aa_margin": round(gm[(sb, what)], 4), "noninferior": hi <= gm[(sb, what)]}
            if hi > gm[(sb, what)]:
                res["worse"].append(f"g_{sb}_{what}")
        res["g"][sb] = info
    res["verdict"] = "NONINFERIOR" if not res["worse"] else "WORSE"
    json.dump(res, open(outp, "w"), indent=1)
    return res


def main(root, gpath, out):
    os.makedirs(out, exist_ok=True)
    aa = os.path.join(out, "aa_x_b.json")
    NJ.aa(aa, [os.path.join(root, "best_b_s0"), os.path.join(root, "best_b_s1")])
    grows = PC.jl(gpath)
    sub = {r["id"]: PC.GSUB[r["gset"]] for r in grows}
    gm = gmargins(root, grows, sub)
    summ = {}
    for name, xs, ys in (("b_vs_f35d", ["best_b_s0", "best_b_s1"], ["f35_d", "f35_d"]),
                         ("a_vs_f35d", ["best_a_s0"], ["f35_d"]),
                         ("a_vs_b", ["best_a_s0"], ["best_b_s0"])):
        r = compare(root, xs, ys, grows, sub, gm, aa, os.path.join(out, f"verdict_{name}.json"))
        summ[name] = {"verdict": r["verdict"], "worse": r["worse"]}
    json.dump(summ, open(os.path.join(out, "verdict_summary.json"), "w"), indent=1)
    print(json.dumps(summ))


if __name__ == "__main__":
    main(*sys.argv[1:4])
