"""prereg_se2e_motion_confirm verdict (fixed before any run): cells (single, none) and (single, motion) x seeds 1, 2
on the causal-velocity data version se2e_c1.

Inputs: per run the `stageb_train predict` jsonl of its last/ checkpoint (item records; the same val keys in every
run) and the transition flags (tools/se2e_temporal.py transition).
  python tools/se2e/motion_confirm_verdict.py --pred none_s1=F motion_s1=F none_s2=F motion_s2=F --trans F --out JSON
Metrics per run (= temporal_verdict.metrics): acc / NLL on ALL items, TRANSITION and STEADY strata, per question.
Effect of seed s = acc(motion_s) - acc(none_s); POOLED effect = mean over the two seeds. Snapshot-cluster bootstrap
(10,000 draws, seed 0, the same resampled snapshots for all four runs, pooled effect per draw), 95 % percentile.
Rule: CONFIRMED iff pooled overall effect >= +0.015 AND its bootstrap 2.5 % bound > 0 AND pooled transition-stratum
effect >= -0.01; otherwise NOT CONFIRMED. Seed spread = effect(s2) - effect(s1) (reported, not in the rule).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from temporal_verdict import CMP_EPS, load_items, metrics  # noqa: E402

RUNS = ("none_s1", "motion_s1", "none_s2", "motion_s2")
SEEDS = ("s1", "s2")
MIN_GAIN, MAX_TRANS_DROP = 0.015, 0.01
N_BOOT, SEED = 10_000, 0
STRATA = ("all", "transition", "steady")


def _ge(x, t):
    return x >= t - CMP_EPS * max(1.0, abs(t))


def effects(m, key="acc"):
    per = {s: {st: m[f"motion_{s}"][st][key] - m[f"none_{s}"][st][key] for st in STRATA} for s in SEEDS}
    pooled = {st: float(np.mean([per[s][st] for s in SEEDS])) for st in STRATA}
    spread = {st: per["s2"][st] - per["s1"][st] for st in STRATA}
    return per, pooled, spread


def bootstrap(items, flags):
    keys = sorted({r["key"] for r in items[RUNS[0]]})
    idx = {k: i for i, k in enumerate(keys)}
    acc = {c: np.zeros(len(keys)) for c in RUNS}
    cnt = np.zeros(len(keys))
    for c in RUNS:
        for r in items[c]:
            acc[c][idx[r["key"]]] += r["correct"]
    for r in items[RUNS[0]]:
        cnt[idx[r["key"]]] += 1
    trans = np.array([flags[k]["transition"] for k in keys])
    rng = np.random.default_rng(SEED)
    out = {}
    for name, mask in (("all", np.ones(len(keys), bool)), ("transition", trans), ("steady", ~trans)):
        ks = np.flatnonzero(mask)
        draws = []
        for _ in range(N_BOOT):
            b = rng.choice(ks, len(ks), replace=True)
            a = {c: acc[c][b].sum() / cnt[b].sum() for c in RUNS}
            draws.append(0.5 * ((a["motion_s1"] - a["none_s1"]) + (a["motion_s2"] - a["none_s2"])))
        out[name] = [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", nargs=4, required=True, help="run=path for none_s1 motion_s1 none_s2 motion_s2")
    ap.add_argument("--trans", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="", help="evaluation set name recorded in the output (e.g. val1799)")
    a = ap.parse_args()
    paths = dict(x.split("=", 1) for x in a.pred)
    if set(paths) != set(RUNS):
        raise SystemExit(f"--pred runs {sorted(paths)} != {RUNS}")
    flags = json.load(open(a.trans))["flags"]
    items, summ, m = {}, {}, {}
    for c in RUNS:
        items[c], summ[c] = load_items(paths[c])
        m[c] = metrics(items[c], flags)
        if summ[c] is not None:  # the item records reproduce evaluate()'s aggregate
            assert abs(m[c]["all"]["acc"] - summ[c]["dec_acc"]) < 1e-9, c
            assert abs(m[c]["all"]["nll"] - summ[c]["dec"]) < 1e-5, c
    keysets = {c: sorted({r["key"] for r in items[c]}) for c in RUNS}
    assert all(v == keysets[RUNS[0]] for v in keysets.values()), "runs evaluated on different val keys"
    per, pooled, spread = effects(m)
    per_nll, pooled_nll, _ = effects(m, "nll")
    boot = bootstrap(items, flags)
    c_point = _ge(pooled["all"], MIN_GAIN)
    c_lower = boot["all"][0] > 0
    c_trans = _ge(pooled["transition"], -MAX_TRANS_DROP)
    verdict = {"pooled_overall": pooled["all"], "lower_95": boot["all"][0], "pooled_transition": pooled["transition"],
               "c_point": bool(c_point), "c_lower": bool(c_lower), "c_transition": bool(c_trans),
               "confirmed": bool(c_point and c_lower and c_trans)}
    out = {"label": a.label, "runs": m, "per_seed_effect": per, "pooled_effect": pooled, "seed_spread": spread,
           "per_seed_effect_nll": per_nll, "pooled_effect_nll": pooled_nll, "bootstrap_95": boot, "verdict": verdict,
           "rule": {"min_gain": MIN_GAIN, "lower_bound_gt": 0.0, "max_transition_drop": MAX_TRANS_DROP,
                    "n_boot": N_BOOT, "seed": SEED},
           "n_val_snapshots": len(keysets[RUNS[0]]),
           "val_keys_summary_sha": {c: (summ[c] or {}).get("val_keys_sha") for c in RUNS}}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({"label": a.label, "verdict": verdict, "per_seed": per, "spread": spread}, indent=1))


if __name__ == "__main__":
    main()
