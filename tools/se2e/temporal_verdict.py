"""prereg_se2e_temporal §6 verdict (fixed before any result): 2x2 cells {single, video2} x {none, motion}.

Inputs: per cell the `stageb_train predict` jsonl of its last/ checkpoint on the 300 val subset (one 'item' record
per decision item: key, question, target, pred, correct, lp = option-set renormalized log-probs), the transition
flags (tools/se2e_temporal.py transition) and the latency json (tools/se2e/temporal_latency.py).
  python tools/se2e/temporal_verdict.py --pred single+none=F ... --trans F --lat F --out JSON
Metrics: dec_acc = mean item correctness, nll = mean -log p~(target set) (= evaluate() 'dec'), on ALL items, on the
TRANSITION stratum (items of snapshots whose frame-level label changes within the next 3 steps / 0.3 s) and on the
rest (STEADY); per question. Main effect of a factor = mean over the other factor's two levels of (on - off);
interaction = (video2+motion - video2+none) - (single+motion - single+none). Adoption (per factor): main effect on
overall acc >= +0.02 AND main effect on transition acc >= -0.01 AND decide p95 (FULL) increase <= 10 %.
Bootstrap (reading aid, not in the rule): snapshot-cluster, 10,000 draws, seed 0, 95 % percentile intervals.
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np

CELLS = ("single+none", "video2+none", "single+motion", "video2+motion")
QUESTIONS = ("dir_xy", "dir_z", "mag_coarse")
MIN_GAIN, MAX_TRANS_DROP, MAX_P95_INC = 0.02, 0.01, 0.10
CMP_EPS = 1e-12  # §74 / §77 supplement 2: relative tolerance on threshold comparisons
N_BOOT, SEED = 10_000, 0


def _ge(x, t):
    return x >= t - CMP_EPS * max(1.0, abs(t))


def _le(x, t):
    return x <= t + CMP_EPS * max(1.0, abs(t))


def load_items(path):
    items = [json.loads(x) for x in open(path)]
    summ = [r for r in items if r.get("event") == "summary"]
    items = [r for r in items if r.get("event") == "item"]
    for r in items:
        lp = [r["lp"][t] for t in r["target"]]
        m = max(lp)
        r["nll"] = -(m + math.log(sum(math.exp(v - m) for v in lp)))
    return items, (summ[-1] if summ else None)


def metrics(items, flags):
    def agg(xs):
        return {"n_items": len(xs), "n_snap": len({r["key"] for r in xs}),
                "acc": float(np.mean([r["correct"] for r in xs])) if xs else None,
                "nll": float(np.mean([r["nll"] for r in xs])) if xs else None}
    tr = [r for r in items if flags[r["key"]]["transition"]]
    st = [r for r in items if not flags[r["key"]]["transition"]]
    out = {"all": agg(items), "transition": agg(tr), "steady": agg(st)}
    for q in QUESTIONS:
        xs = [r for r in items if r["question"] == q]
        out[f"q_{q}"] = agg(xs)
        out[f"q_{q}_item_transition"] = agg([r for r in xs if flags[r["key"]]["per_q"][q]])
    return out


def main_effects(m, stratum, key="acc"):
    g = lambda c: m[c][stratum][key]  # noqa: E731
    return {"V": 0.5 * ((g("video2+none") - g("single+none")) + (g("video2+motion") - g("single+motion"))),
            "M": 0.5 * ((g("single+motion") - g("single+none")) + (g("video2+motion") - g("video2+none"))),
            "VxM": (g("video2+motion") - g("video2+none")) - (g("single+motion") - g("single+none"))}


def bootstrap(items_by_cell, flags):
    keys = sorted({r["key"] for r in items_by_cell[CELLS[0]]})
    idx = {k: i for i, k in enumerate(keys)}
    acc = {c: np.zeros(len(keys)) for c in CELLS}
    cnt = np.zeros(len(keys))
    for c in CELLS:
        for r in items_by_cell[c]:
            acc[c][idx[r["key"]]] += r["correct"]
    for r in items_by_cell[CELLS[0]]:
        cnt[idx[r["key"]]] += 1
    trans = np.array([flags[k]["transition"] for k in keys])
    rng = np.random.default_rng(SEED)
    out = {}
    for name, mask in (("all", np.ones(len(keys), bool)), ("transition", trans)):
        ks = np.flatnonzero(mask)
        draws = {"V": [], "M": [], "VxM": []}
        for _ in range(N_BOOT):
            b = rng.choice(ks, len(ks), replace=True)
            a = {c: acc[c][b].sum() / cnt[b].sum() for c in CELLS}
            draws["V"].append(0.5 * (a["video2+none"] - a["single+none"] + a["video2+motion"] - a["single+motion"]))
            draws["M"].append(0.5 * (a["single+motion"] - a["single+none"] + a["video2+motion"] - a["video2+none"]))
            draws["VxM"].append(a["video2+motion"] - a["video2+none"] - a["single+motion"] + a["single+none"])
        out[name] = {k: [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] for k, v in draws.items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", nargs=4, required=True, help="cell=path for the four cells")
    ap.add_argument("--trans", required=True)
    ap.add_argument("--lat", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    paths = dict(x.split("=", 1) for x in a.pred)
    if set(paths) != set(CELLS):
        raise SystemExit(f"--pred cells {sorted(paths)} != {CELLS}")
    flags = json.load(open(a.trans))["flags"]
    items, summ, m = {}, {}, {}
    for c in CELLS:
        items[c], summ[c] = load_items(paths[c])
        m[c] = metrics(items[c], flags)
        if summ[c] is not None:  # the item records reproduce evaluate()'s aggregate
            assert abs(m[c]["all"]["acc"] - summ[c]["dec_acc"]) < 1e-9, c
            assert abs(m[c]["all"]["nll"] - summ[c]["dec"]) < 1e-5, c
    keysets = {c: sorted({r["key"] for r in items[c]}) for c in CELLS}
    assert all(v == keysets[CELLS[0]] for v in keysets.values()), "cells evaluated on different val keys"
    lat = json.load(open(a.lat))["formats"]
    eff = {s: main_effects(m, s) for s in ("all", "transition", "steady")}
    eff_nll = {s: main_effects(m, s, "nll") for s in ("all", "transition", "steady")}
    p95 = {c: lat[c]["full_p95"] for c in CELLS}
    p95_inc = {"V": p95["video2+none"] / p95["single+none"] - 1, "M": p95["single+motion"] / p95["single+none"] - 1}
    verdict = {}
    for f in ("V", "M"):
        c1 = _ge(eff["all"][f], MIN_GAIN)
        c2 = _ge(eff["transition"][f], -MAX_TRANS_DROP)
        c3 = _le(p95_inc[f], MAX_P95_INC)
        verdict[f] = {"overall_main_effect": eff["all"][f], "transition_main_effect": eff["transition"][f],
                      "p95_increase": p95_inc[f], "c1_gain": c1, "c2_transition": c2, "c3_latency": c3,
                      "adopt": bool(c1 and c2 and c3)}
    out = {"cells": m, "main_effects_acc": eff, "main_effects_nll": eff_nll, "latency": lat, "verdict": verdict,
           "interaction_acc": {s: eff[s]["VxM"] for s in eff}, "bootstrap_acc_95": bootstrap(items, flags),
           "rule": {"min_gain": MIN_GAIN, "max_transition_drop": MAX_TRANS_DROP, "max_p95_increase": MAX_P95_INC},
           "n_val_snapshots": len(keysets[CELLS[0]])}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({"verdict": verdict, "interaction": out["interaction_acc"]}, indent=1))


if __name__ == "__main__":
    main()
