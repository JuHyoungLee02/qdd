"""Main 35B judge (docs/stage3/prereg_main35.md).
1. best checkpoint among the evaluated ones (ep2, 1.5, 2.5, 1, 3 with EVAL_COMPLETE): lowest L8S-validation >20 mm
   failure rate (no goal = failure); tie -> higher open-point validation hit; tie -> the later checkpoint.
2. best vs f35_d with the E-C35 35B A/A margins (arm b seeds 0 / 1: aa_x_b.json for L8-X dev / OOD-H / OOD-O / OOD-O58,
   G margins from the same pair) - tools/final35/c35_judge.compare (ni_judge rule, user-log 186).
usage: python main35_judge.py <out dir>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c35_judge as CJ  # noqa: E402

M = "/data/harvest/out/main35"
C35 = "/data/harvest/out/c35"
G = "/data/harvest/out/opratio/g_eval.jsonl"


def val_score(d):
    e = []
    for x in open(os.path.join(d, "x_val_l8s_d-min_clean", "scores.jsonl")):
        r = json.loads(x)
        if r.get("approach_row"):
            v = r.get("approach_3d_mm")
            e.append(1e6 if v is None else float(v))
    g = [json.loads(x) for x in open(os.path.join(d, "g_val_open", "scores.jsonl"))]
    return sum(v > 20.0 for v in e) / max(1, len(e)), sum(bool(r.get("hit")) for r in g) / max(1, len(g))


def main(out):
    os.makedirs(out, exist_ok=True)
    cands = {}
    for e in ("1", "1.5", "2", "2.5", "3"):
        d = os.path.join(M, "eval", f"ep{e}")
        if os.path.exists(os.path.join(d, "EVAL_COMPLETE")):
            cands[e] = val_score(d)
    best = min(cands, key=lambda e: (cands[e][0], -cands[e][1], -float(e)))
    root = os.path.join(out, "root")
    os.makedirs(root, exist_ok=True)
    for name, tgt in (("main_best", os.path.join(M, "eval", f"ep{best}")), ("f35_d", os.path.join(C35, "eval", "f35_d")),
                      ("best_b_s0", os.path.join(C35, "eval", "best_b_s0")),
                      ("best_b_s1", os.path.join(C35, "eval", "best_b_s1"))):
        p = os.path.join(root, name)
        if os.path.islink(p):
            os.remove(p)
        os.symlink(tgt, p)
    grows = CJ.PC.jl(G)
    sub = {r["id"]: CJ.PC.GSUB[r["gset"]] for r in grows}
    gm = CJ.gmargins(root, grows, sub)
    r = CJ.compare(root, ["main_best"], ["f35_d"], grows, sub, gm, os.path.join(C35, "verdict", "aa_x_b.json"),
                   os.path.join(out, "verdict_main_vs_f35d.json"))
    summ = {"checkpoints": {e: {"val_fail": round(v[0], 4), "val_open_hit": round(v[1], 4)} for e, v in cands.items()},
            "best": best, "verdict": r["verdict"], "worse": r["worse"]}
    json.dump(summ, open(os.path.join(out, "verdict_summary.json"), "w"), indent=1)
    print(json.dumps(summ))


if __name__ == "__main__":
    main(sys.argv[1])
