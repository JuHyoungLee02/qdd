"""Stage-A SFT test on DEV (docs/stage3/results/stageA_sft.md prereg): SFT vs zero-shot vs majority, labels_v2.

usage: python stagea_sft_report.py --dev /data/harvest/data/jsel_dev --zero ZERO.jsonl --sft SFT.jsonl --out JSON
ZERO / SFT = tools/jevl_e3lite.py acc rows (S1 1 mm, head image, fixed order) of the base and the merged SFT model.
The rows' own `correct` (vs the old oracle) is ignored: every gated item is re-scored by option_key against
labels_v2 (<dev>/P*.labels_v2.jsonl); argmax NONE_ESCALATE or a failed call = wrong. progress (not trained, no
label) is reported as drift only.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harvest.analysis.stats import auroc, cluster_mean_ci, ece  # noqa: E402

GATED = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")
V2_FIELD = {"dir_xy": "dir_xy", "dir_z": "dir_z", "mag_coarse": "mag_coarse", "target": "target",
            "phase": "phase_choice"}
NE = "NONE_ESCALATE"


def read_labels(dev):
    out = {}
    for kind in ("P0", "P1", "P2"):
        for x in open(f"{dev}/{kind}.labels_v2.jsonl", encoding="utf-8"):
            r = json.loads(x)
            out[f"{r['kind']}_s{r['seed']}_k{r['k']}"] = r["labels_v2"]
    return out


def items(rows, labels):
    """{(snap, question): item} for the gated questions, re-scored against labels_v2."""
    out = {}
    for r in rows:
        q = r["question"]
        if q not in GATED:
            continue
        y = labels[r["snap"]][V2_FIELD[q]]
        probs = r.get("probs") or {}
        out[(r["snap"], q)] = {"cluster": (r["kind"], r["seed"]), "q": q, "y": y, "key": r["key"],
                               "correct": r["key"] is not None and r["key"] == y, "p": r["p_chosen"],
                               "p_ne": probs.get(NE), "error": r.get("error")}
    return out


def mean_ci(pairs):
    d = defaultdict(list)
    for c, v in pairs:
        d[c].append(v)
    v = [x for xs in d.values() for x in xs]
    lo, hi = cluster_mean_ci(d)
    return {"mean": round(float(np.mean(v)), 4), "ci": [round(lo, 4), round(hi, 4)], "n": len(v)}


def summarize(Z, S, keys, maj):
    res = {}
    for name, sel in [("pooled", keys)] + [(q, [k for k in keys if k[1] == q]) for q in GATED]:
        z = [(Z[k]["cluster"], int(Z[k]["correct"])) for k in sel]
        s = [(S[k]["cluster"], int(S[k]["correct"])) for k in sel]
        m = [(S[k]["cluster"], int(maj[k[1]] == S[k]["y"])) for k in sel]
        r = {"n": len(sel), "zero": mean_ci(z), "sft": mean_ci(s), "majority": mean_ci(m),
             "sft_minus_zero": mean_ci([(a[0], a[1] - b[1]) for a, b in zip(s, z)]),
             "sft_minus_majority": mean_ci([(a[0], a[1] - b[1]) for a, b in zip(s, m)]),
             "zero_minus_majority": mean_ci([(a[0], a[1] - b[1]) for a, b in zip(z, m)])}
        for tag, M in (("zero", Z), ("sft", S)):
            p = [M[k]["p"] if M[k]["p"] is not None else 0.0 for k in sel]
            c = [M[k]["correct"] for k in sel]
            pne = [M[k]["p_ne"] for k in sel if M[k]["p_ne"] is not None]
            a = auroc(p, c)
            r[f"{tag}_ece"] = round(ece(p, c), 4)
            r[f"{tag}_auroc"] = None if a is None else round(a, 4)
            r[f"{tag}_p_ne_mean"] = float(np.mean(pne)) if pne else None
            r[f"{tag}_ne_argmax_rate"] = round(float(np.mean([M[k]["key"] == NE for k in sel])), 5)
            r[f"{tag}_errors"] = sum(M[k]["error"] is not None for k in sel)
            if name != "pooled":
                r[f"{tag}_choices"] = dict(Counter(M[k]["key"] for k in sel).most_common())
        if name != "pooled":
            r["label_dist"] = dict(Counter(S[k]["y"] for k in sel).most_common())
            r["majority_label"] = maj[name]
        res[name] = r
    return res


def progress_drift(zr, sr):
    z = {r["snap"]: r for r in zr if r["question"] == "progress"}
    s = {r["snap"]: r for r in sr if r["question"] == "progress"}
    ks = sorted(set(z) & set(s))
    dp = [max(abs(s[k]["probs"][n] - z[k]["probs"][n]) for n in z[k]["probs"]) for k in ks
          if z[k].get("probs") and s[k].get("probs")]
    return {"n": len(ks), "zero_choices": dict(Counter(z[k]["key"] for k in ks).most_common()),
            "sft_choices": dict(Counter(s[k]["key"] for k in ks).most_common()),
            "argmax_agree_zero_sft": round(float(np.mean([z[k]["key"] == s[k]["key"] for k in ks])), 4),
            "maxabs_dp_median": round(float(np.median(dp)), 4) if dp else None,
            "maxabs_dp_p95": round(float(np.quantile(dp, 0.95)), 4) if dp else None,
            "ref_acc_vs_old_oracle_zero": round(float(np.mean([z[k]["key"] == z[k]["oracle"] for k in ks])), 4),
            "ref_acc_vs_old_oracle_sft": round(float(np.mean([s[k]["key"] == s[k]["oracle"] for k in ks])), 4),
            "p_ne_mean_zero": float(np.mean([z[k]["probs"].get(NE, 0) for k in ks if z[k].get("probs")])),
            "p_ne_mean_sft": float(np.mean([s[k]["probs"].get(NE, 0) for k in ks if s[k].get("probs")]))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--zero", required=True)
    ap.add_argument("--sft", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    labels = read_labels(a.dev)
    zr = [json.loads(x) for x in open(a.zero, encoding="utf-8")]
    sr = [json.loads(x) for x in open(a.sft, encoding="utf-8")]
    Z, S = items(zr, labels), items(sr, labels)
    keys = sorted(set(Z) & set(S))
    keys = [(k, S[k]["cluster"]) for k in keys]
    ks = [k for k, _ in keys]
    maj = {q: Counter(S[k]["y"] for k in ks if k[1] == q).most_common(1)[0][0] for q in GATED}
    res = {"n_items": len(ks), "n_snap": len({k[0] for k in ks}), "n_clusters": len({c for _, c in keys}),
           "only_zero": len(set(Z) - set(S)), "only_sft": len(set(S) - set(Z)),
           "models": [zr[0]["model"], sr[0]["model"]], "cond": [sr[0].get("S"), sr[0].get("step_cm"),
                                                                 sr[0].get("inp"), sr[0].get("order")],
           **summarize(Z, S, ks, maj), "progress_drift": progress_drift(zr, sr)}
    res["per_kind"] = {kind: summarize(Z, S, [k for k in ks if S[k]["cluster"][0] == kind], maj)["pooled"]
                       for kind in ("P0", "P1", "P2")}
    p = res["pooled"]
    res["criteria"] = {
        "a_sft_minus_zero_lower_gt_0": p["sft_minus_zero"]["ci"][0] > 0,
        "b_sft_minus_majority_lower_gt_0": p["sft_minus_majority"]["ci"][0] > 0,
        "b_ref_sft_ci_lower_gt_majority_point": p["sft"]["ci"][0] > p["majority"]["mean"],
        "d_questions_below_majority": [q for q in GATED if res[q]["sft"]["mean"] < res[q]["majority"]["mean"]]}
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps({"pooled": p, "criteria": res["criteria"],
                      "per_q": {q: [res[q]["zero"]["mean"], res[q]["sft"]["mean"], res[q]["majority"]["mean"]]
                                for q in GATED}}, indent=1))


if __name__ == "__main__":
    main()
