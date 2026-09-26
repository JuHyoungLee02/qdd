"""E-CONF path-reproduction gate G1 (docs/stage3/prereg_conf.md §4): the extraction must reproduce earlier records of
the same checkpoint on the overlapping snapshots with the same flow-noise numbering -- predicted decisions agree
>= 0.99 per (snapshot, question), chunk-MSE mean ratio within 1 +- 0.02 and per-snapshot relative difference median
<= 0.01, and (when the reference has margins) margin median absolute difference <= 0.02. Agreement values only; no
confidence-vs-error value is computed here.
  python tools/conf/conf_gate.py MINE.jsonl REF.jsonl [REF2.jsonl ...]    (prints one json; rc 1 when failing)
  references: E-NOV0 eval.meta.jsonl (C0), E-SR1c eval_c1.jsonl (C1), E-SR0 sr0_motion_s{1,2}.jsonl (S-E2E)
"""
from __future__ import annotations

import json
import sys

import numpy as np

TH = {"pred_agree": 0.99, "mse_ratio_tol": 0.02, "mse_med_rel": 0.01, "margin_med_abs": 0.02}


def _margin(lp):
    v = sorted((float(x) for x in lp.values()), reverse=True)
    return v[0] - v[1] if len(v) > 1 else 99.0


def ref_record(d: dict) -> dict:
    if "c" in d:
        return {"preds": d["preds"], "mse": float(d["c"]["pred"][5]), "margin": None}
    return {"preds": d["preds"], "mse": float(d["mse"]), "margin": d.get("margin")}


def gate(mine, ref: dict) -> dict:
    agree, n_q, ratio_a, ratio_b, rel, mad = 0, 0, [], [], [], []
    n = 0
    for r in mine:
        x = ref.get(r["id"])
        if x is None:
            continue
        n += 1
        for q, d in r["q"].items():
            if q in x["preds"]:
                n_q += 1
                agree += d["pred"] == x["preds"][q]
            if x["margin"] and q in x["margin"]:
                mad.append(abs(_margin(d["lp"]) - float(x["margin"][q])))
        ratio_a.append(r["mse"])
        ratio_b.append(x["mse"])
        rel.append(abs(r["mse"] - x["mse"]) / max(abs(x["mse"]), 1e-12))
    if n == 0:
        return {"n_overlap": 0, "pass": False}
    out = {"n_overlap": n, "n_pairs": n_q, "pred_agree": agree / n_q if n_q else 0.0,
           "mse_ratio": float(np.mean(ratio_a) / np.mean(ratio_b)), "mse_med_rel": float(np.median(rel)),
           "margin_med_abs": float(np.median(mad)) if mad else None, "thresholds": TH}
    out["pass"] = bool(out["pred_agree"] >= TH["pred_agree"] and abs(out["mse_ratio"] - 1) <= TH["mse_ratio_tol"]
                       and out["mse_med_rel"] <= TH["mse_med_rel"]
                       and (out["margin_med_abs"] is None or out["margin_med_abs"] <= TH["margin_med_abs"]))
    return out


def load_ref(paths) -> dict:
    ref = {}
    for p in paths:
        for x in open(p, encoding="utf-8"):
            d = json.loads(x)
            if "preds" in d and "id" in d:
                ref[d["id"]] = ref_record(d)
    return ref


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    mine = [json.loads(x) for x in open(argv[0], encoding="utf-8")]
    mine = [r for r in mine if r.get("event") != "summary"]
    g = gate(mine, load_ref(argv[1:]))
    print(json.dumps(g))
    sys.exit(0 if g["pass"] else 1)


if __name__ == "__main__":
    main()
