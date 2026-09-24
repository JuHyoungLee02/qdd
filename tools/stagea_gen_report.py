"""Stage-A generalization (docs/stage3/results/stageA_generalize.md prereg): zero-shot vs SFT on DEV snapshots of the
standard / random / dr scenes (labels_v2, S1 1 mm), RD = A_standard - A_variant paired by (seed, kind, k), and the
image ablation (img vs txt, same checkpoint).

usage: python stagea_gen_report.py --dirs standard=/data/harvest/data/jsel_dev,random=.../gen_dev/random,dr=.../dr \
           --res /data/harvest/stageA_gen [--old /data/harvest/stageA_sft] --out JSON
Acc rows: <res>/<variant>/acc_<model>_S1_g0.1_<img|txt>_fixed.jsonl (tools/jevl_e3lite.py acc). Rows are re-scored
against that variant's labels_v2 (stagea_sft_report.items); the rows' old-oracle `correct` is ignored.
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harvest.analysis.stats import cluster_diff_ci  # noqa: E402
from stagea_sft_report import GATED, V2_FIELD, items, mean_ci, read_labels  # noqa: E402

MODELS = {"zero": "Qwen3-VL-4B-Instruct", "sft": "jevl-sftA"}
VARIANTS = ("standard", "random", "dr")


def common(A, B):
    return sorted(set(A) & set(B))


def paired_diff(A, B, keys):
    """mean over keys of correct_A - correct_B, episode-cluster CI (items matched by key)."""
    return mean_ci([(A[k]["cluster"], int(A[k]["correct"]) - int(B[k]["correct"])) for k in keys])


def diff_of_diffs(SA, SB, ZA, ZB, keys):
    """(S_A - S_B) - (Z_A - Z_B) per matched item, e.g. RD_SFT - RD_zero."""
    return mean_ci([(SA[k]["cluster"], (int(SA[k]["correct"]) - int(SB[k]["correct"]))
                     - (int(ZA[k]["correct"]) - int(ZB[k]["correct"]))) for k in keys])


def majority(I, keys):
    """Per-question most frequent label over the given items (that variant's own labels)."""
    c = defaultdict(Counter)
    for k in keys:
        c[k[1]][I[k]["y"]] += 1
    return {q: v.most_common(1)[0][0] for q, v in c.items()}


def majority_items(I, maj):
    """Items of the always-pick-the-majority rule, same structure as items()."""
    return {k: {**v, "key": maj[k[1]], "correct": maj[k[1]] == v["y"]} for k, v in I.items()}


def acc(I, keys):
    return mean_ci([(I[k]["cluster"], int(I[k]["correct"])) for k in keys])


def unpaired_diff(A, ka, B, kb, n=10000):
    """A(all its items) - B(all its items), jointly resampled episodes (same (kind, seed) ids in both)."""
    a, b = defaultdict(list), defaultdict(list)
    for k in ka:
        a[A[k]["cluster"]].append(int(A[k]["correct"]))
    for k in kb:
        b[B[k]["cluster"]].append(int(B[k]["correct"]))
    ma = np.mean([x for v in a.values() for x in v])
    mb = np.mean([x for v in b.values() for x in v])
    lo, hi = cluster_diff_ci(a, b, n=n)
    return {"mean": round(float(ma - mb), 4), "ci": [round(lo, 4), round(hi, 4)], "n": [len(ka), len(kb)]}


def pair_meta(std, var, questions):
    """std / var: {snap: {"phase": planner phase, "labels": {q: label}}} -> pairing counts and agreement."""
    ks = sorted(set(std) & set(var))
    return {"n_std": len(std), "n_var": len(var), "n_paired": len(ks),
            "same_phase": round(float(np.mean([std[k]["phase"] == var[k]["phase"] for k in ks])), 4) if ks else None,
            "same_label": {q: round(float(np.mean([std[k]["labels"][q] == var[k]["labels"][q] for k in ks])), 4)
                           for q in questions} if ks else None}


def snap_info(dev, labels):
    """{snap: {phase, labels}} for the scored snapshots (oracle != null, same as jevl_acc.snapshots)."""
    out = {}
    for kind in ("P0", "P1", "P2"):
        for p in glob.glob(f"{dev}/{kind}/ep*.jsonl"):
            for x in open(p, encoding="utf-8"):
                ln = json.loads(x)
                if ln["oracle"] is None:
                    continue
                s = f"{kind}_s{ln['seed']}_k{ln['k']}"
                out[s] = {"phase": ln["phase"], "labels": {q: labels[s][V2_FIELD[q]] for q in GATED}}
    return out


def by_q(keys):
    return [("pooled", keys)] + [(q, [k for k in keys if k[1] == q]) for q in GATED]


def load(res, variant, model, inp, labels):
    p = f"{res}/{variant}/acc_{model}_S1_g0.1_{inp}_fixed.jsonl"
    if not os.path.exists(p):
        return None
    return items([json.loads(x) for x in open(p, encoding="utf-8")], labels)


def determinism(old_path, new_rows_path):
    o = {(r["snap"], r["question"]): r for r in map(json.loads, open(old_path, encoding="utf-8"))}
    n = {(r["snap"], r["question"]): r for r in map(json.loads, open(new_rows_path, encoding="utf-8"))}
    ks = sorted(set(o) & set(n))
    dp = [max(abs(o[k]["probs"][x] - n[k]["probs"][x]) for x in o[k]["probs"]) for k in ks
          if o[k].get("probs") and n[k].get("probs")]
    return {"n": len(ks), "key_agree": round(float(np.mean([o[k]["key"] == n[k]["key"] for k in ks])), 6),
            "max_abs_dp": float(max(dp)) if dp else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", required=True)
    ap.add_argument("--res", required=True)
    ap.add_argument("--old", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    dirs = dict(x.split("=", 1) for x in a.dirs.split(","))
    labels = {v: read_labels(dirs[v]) for v in VARIANTS}
    info = {v: snap_info(dirs[v], labels[v]) for v in VARIANTS}
    I = {(m, v, inp): load(a.res, v, name, inp, labels[v])
         for m, name in MODELS.items() for v in VARIANTS for inp in ("img", "txt")}
    I = {k: x for k, x in I.items() if x is not None}
    out = {"files": sorted(f"{m}/{v}/{inp}" for m, v, inp in I), "pairing": {}}
    K = {k: sorted(x) for k, x in I.items()}
    # A per model x variant x input, majority per variant
    out["A"], out["majority"] = {}, {}
    for v in VARIANTS:
        base = I.get(("sft", v, "img"))
        if base is None:
            continue
        kv = K[("sft", v, "img")]
        maj = majority(base, kv)
        M = majority_items(base, maj)
        out["majority"][v] = {"labels": maj, **{n: acc(M, ks) for n, ks in by_q(kv)}}
        out[f"sft_minus_majority_{v}"] = {n: paired_diff(base, M, ks) for n, ks in by_q(kv)}
        if ("zero", v, "img") in I:
            out[f"zero_minus_majority_{v}"] = {n: paired_diff(I[("zero", v, "img")], M, ks)
                                               for n, ks in by_q(common(I[("zero", v, "img")], M))}
        for (m, vv, inp), X in I.items():
            if vv == v:
                out["A"][f"{m}/{v}/{inp}"] = {n: acc(X, ks) for n, ks in by_q(K[(m, v, inp)])}
                out["A"][f"{m}/{v}/{inp}"]["per_kind"] = {
                    kind: acc(X, [k for k in K[(m, v, inp)] if X[k]["cluster"][0] == kind]) for kind in ("P0", "P1",
                                                                                                         "P2")}
                out["A"][f"{m}/{v}/{inp}"]["choices"] = {
                    q: dict(Counter(X[k]["key"] for k in K[(m, v, inp)] if k[1] == q).most_common()) for q in GATED}
                out["A"][f"{m}/{v}/{inp}"]["errors"] = sum(X[k]["error"] is not None for k in X)
        out["majority"][v]["label_dist"] = {q: dict(Counter(base[k]["y"] for k in kv if k[1] == q).most_common())
                                            for q in GATED}
    # RD (paired and unpaired), diff of diffs, per input
    out["RD"], out["dRD"], out["RD_unpaired"], out["img_part_of_RD"] = {}, {}, {}, {}
    for v in ("random", "dr"):
        out["pairing"][v] = pair_meta(info["standard"], info[v], GATED)
        for inp in ("img", "txt"):
            have = all((m, x, inp) in I for m in MODELS for x in ("standard", v))
            if not have:
                continue
            ks = common(common(I[("sft", "standard", inp)], I[("sft", v, inp)]),
                        common(I[("zero", "standard", inp)], I[("zero", v, inp)]))
            for m in MODELS:
                out["RD"][f"{m}/{v}/{inp}"] = {n: paired_diff(I[(m, "standard", inp)], I[(m, v, inp)], kk)
                                               for n, kk in by_q(ks)}
                out["RD_unpaired"][f"{m}/{v}/{inp}"] = unpaired_diff(I[(m, "standard", inp)], K[(m, "standard", inp)],
                                                                     I[(m, v, inp)], K[(m, v, inp)])
            out["dRD"][f"{v}/{inp}"] = {n: diff_of_diffs(I[("sft", "standard", inp)], I[("sft", v, inp)],
                                                         I[("zero", "standard", inp)], I[("zero", v, inp)], kk)
                                        for n, kk in by_q(ks)}
        for m in MODELS:  # RD_img - RD_txt on items present in all four runs
            quad = [I.get((m, x, inp)) for x in ("standard", v) for inp in ("img", "txt")]
            if any(q is None for q in quad):
                continue
            si, vi, st, vt = quad
            ks = sorted(set(si) & set(vi) & set(st) & set(vt))
            out["img_part_of_RD"][f"{m}/{v}"] = {n: diff_of_diffs(si, vi, st, vt, kk) for n, kk in by_q(ks)}
    # image ablation (img - txt, same checkpoint, same items)
    out["img_minus_txt"] = {}
    for (m, v, inp) in I:
        if inp == "img" and (m, v, "txt") in I:
            ks = common(I[(m, v, "img")], I[(m, v, "txt")])
            out["img_minus_txt"][f"{m}/{v}"] = {n: paired_diff(I[(m, v, "img")], I[(m, v, "txt")], kk)
                                                for n, kk in by_q(ks)}
    # SFT image contribution minus zero-shot image contribution (standard)
    if all((m, "standard", x) in I for m in MODELS for x in ("img", "txt")):
        s_i, s_t, z_i, z_t = (I[(m, "standard", x)] for m in ("sft", "zero") for x in ("img", "txt"))
        ks = sorted(set(s_i) & set(s_t) & set(z_i) & set(z_t))
        out["img_contrib_sft_minus_zero_standard"] = diff_of_diffs(s_i, s_t, z_i, z_t, ks)
    if a.old:
        out["determinism_vs_stageA_sft"] = {
            m: determinism(f"{a.old}/acc_{name}_S1_g0.1_img_fixed.jsonl",
                           f"{a.res}/standard/acc_{name}_S1_g0.1_img_fixed.jsonl")
            for m, name in MODELS.items()
            if os.path.exists(f"{a.res}/standard/acc_{name}_S1_g0.1_img_fixed.jsonl")}
    json.dump(out, open(a.out, "w"), indent=1)
    brief = {"A": {k: v["pooled"] for k, v in out["A"].items()}, "RD": {k: v["pooled"] for k, v in out["RD"].items()},
             "dRD": {k: v["pooled"] for k, v in out["dRD"].items()},
             "img_minus_txt": {k: v["pooled"] for k, v in out["img_minus_txt"].items()},
             "majority": {k: v["pooled"] for k, v in out["majority"].items()}, "pairing": out["pairing"]}
    print(json.dumps(brief, indent=1))


if __name__ == "__main__":
    main()
