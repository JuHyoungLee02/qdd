"""prereg_marr §5 verdict (fixed before any A run): C0 = motion_s1 / motion_s2 (reuse checked, prereg §3) vs
A = the same recipe + the trace5-point@v1 aux head, seeds 1 and 2, on se2e_c1 with the motion line.

Inputs: per run the `predict` jsonl of its last/ checkpoint on the FULL val set (1,799 snapshots, item records, the
same val keys in every run), the transition flags (se2e_c1/transition_val.json) and the RB2 label file (which val rows
carry a trace label -- reported stratum only).
  python tools/marr_real/verdict.py --pred c0_s1=F a_s1=F c0_s2=F a_s2=F --trans F --labels F --out JSON
Effect of seed s = acc(a_s) - acc(c0_s) (paired); POOLED = mean over the two seeds. Snapshot-cluster bootstrap
(10,000 draws, seed 0, the same resampled snapshots for all four runs), 95 % percentile -- the rule's statistics are
those of tools/ma1/ma1b_verdict.py (imported, run names mapped). Rule: ADOPT iff pooled overall effect >= +0.02 AND its
bootstrap 2.5 % bound > 0 AND pooled transition-stratum effect >= -0.01 (CMP_EPS 1e-12; the bound strictly > 0); the
third adoption condition (runtime latency unchanged) is established by the byte-identical runtime path (prereg §4),
checked separately (view check) and passed in with --runtime-identical. Reported outside the rule: RB2 stratum and
RB2-labelled-row stratum (pooled effect + the same bootstrap restricted to those snapshots), RB1, NLL, per question.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ma1"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "se2e"))
import ma1b_verdict as MB  # noqa: E402
from temporal_verdict import load_items, metrics  # noqa: E402

NAMES = {"c0_s1": "none_s1", "a_s1": "a3d_s1", "c0_s2": "none_s2", "a_s2": "a3d_s2"}
N_VAL = 1799


def stratum_bootstrap(items, keys_in, n_boot=MB.N_BOOT, seed=MB.SEED):
    """Pooled effect and its snapshot bootstrap 95 % restricted to the snapshots in keys_in."""
    keys = sorted({r["key"] for r in items[MB.RUNS[0]]} & set(keys_in))
    idx = {k: i for i, k in enumerate(keys)}
    acc = {c: np.zeros(len(keys)) for c in MB.RUNS}
    cnt = np.zeros(len(keys))
    for c in MB.RUNS:
        for r in items[c]:
            if r["key"] in idx:
                acc[c][idx[r["key"]]] += r["correct"]
    for r in items[MB.RUNS[0]]:
        if r["key"] in idx:
            cnt[idx[r["key"]]] += 1

    def eff(b):
        a = {c: acc[c][b].sum() / cnt[b].sum() for c in MB.RUNS}
        return 0.5 * ((a["a3d_s1"] - a["none_s1"]) + (a["a3d_s2"] - a["none_s2"]))
    allb = np.arange(len(keys))
    rng = np.random.default_rng(seed)
    draws = [eff(rng.choice(allb, len(allb), replace=True)) for _ in range(n_boot)]
    per = {s: float(acc[f"a3d_{s}"].sum() / cnt.sum() - acc[f"none_{s}"].sum() / cnt.sum()) for s in MB.SEEDS}
    return {"n_snap": len(keys), "n_items": int(cnt.sum()), "pooled": float(eff(allb)), "per_seed": per,
            "ci95": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
            "acc": {c: float(acc[c].sum() / cnt.sum()) for c in MB.RUNS}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", nargs=4, required=True, help="run=path for c0_s1 a_s1 c0_s2 a_s2")
    ap.add_argument("--trans", required=True)
    ap.add_argument("--labels", required=True, help="RB2.tracept.jsonl")
    ap.add_argument("--runtime-identical", choices=["yes", "no"], required=True,
                    help="prereg §4 view check result (A last/ trained view == base view, val 300)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-val", type=int, default=N_VAL, help="expected val snapshots (1,799; tests use fewer)")
    a = ap.parse_args()
    paths = dict(x.split("=", 1) for x in a.pred)
    if set(paths) != set(NAMES):
        raise SystemExit(f"--pred runs {sorted(paths)} != {sorted(NAMES)}")
    flags = json.load(open(a.trans))["flags"]
    items, summ, m = {}, {}, {}
    for ours, theirs in NAMES.items():
        items[theirs], summ[theirs] = load_items(paths[ours])
        keys = [r["key"] for r in items[theirs]]
        if len(set(keys)) != a.n_val or len(keys) != 3 * a.n_val:  # P25: size / duplicates
            raise SystemExit(f"{ours}: {len(set(keys))} snapshots / {len(keys)} items (want {a.n_val} / {3 * a.n_val})")
        m[theirs] = metrics(items[theirs], flags)
        if summ[theirs] is not None:
            assert abs(m[theirs]["all"]["acc"] - summ[theirs]["dec_acc"]) < 1e-9, ours
        m[theirs]["per_source"] = {s: metrics([r for r in items[theirs] if r["key"].split("_")[0] == s],
                                              flags)["all"] for s in MB.SOURCES}
    ks = {c: sorted({r["key"] for r in items[c]}) for c in MB.RUNS}
    if not all(v == ks[MB.RUNS[0]] for v in ks.values()):
        raise SystemExit("runs evaluated on different val keys")
    per, pooled, spread = MB.effects(m)
    per_nll, pooled_nll, _ = MB.effects(m, "nll")
    boot = MB.bootstrap(items, flags)
    lab = {}
    for x in open(a.labels, encoding="utf-8"):
        r = json.loads(x)
        lab[r["key"]] = r["trace255"] is not None
    val = set(ks[MB.RUNS[0]])
    rb2 = {k for k in val if k.startswith("RB2_")}
    missing = rb2 - set(lab)
    if missing:
        raise SystemExit(f"{len(missing)} RB2 val snapshots without a label record")
    strata = {"RB2": stratum_bootstrap(items, rb2), "RB2_labelled": stratum_bootstrap(items, {k for k in rb2 if lab[k]}),
              "RB2_unlabelled": stratum_bootstrap(items, {k for k in rb2 if not lab[k]}),
              "RB1": stratum_bootstrap(items, {k for k in val if k.startswith("RB1_")})}
    c_point = MB._ge(pooled["all"], MB.MIN_GAIN)
    c_lower = boot["all"][0] > 0
    c_trans = MB._ge(pooled["transition"], -MB.MAX_TRANS_DROP)
    c_lat = a.runtime_identical == "yes"
    verdict = {"pooled_overall": pooled["all"], "lower_95": boot["all"][0], "pooled_transition": pooled["transition"],
               "c_point": bool(c_point), "c_lower": bool(c_lower), "c_transition": bool(c_trans),
               "c_runtime_unchanged": c_lat, "adopt": bool(c_point and c_lower and c_trans and c_lat)}
    out = {"runs": {k: m[v] for k, v in NAMES.items()}, "per_seed_effect": per, "pooled_effect": pooled,
           "seed_spread": spread, "per_seed_effect_nll": per_nll, "pooled_effect_nll": pooled_nll,
           "bootstrap_95": boot, "strata": strata, "verdict": verdict,
           "rule": {"min_gain": MB.MIN_GAIN, "lower_bound_gt": 0.0, "max_transition_drop": MB.MAX_TRANS_DROP,
                    "n_boot": MB.N_BOOT, "seed": MB.SEED, "cmp_eps": MB.CMP_EPS},
           "n_val_snapshots": len(val), "val_keys_summary_sha": {c: (summ[c] or {}).get("val_keys_sha") for c in MB.RUNS},
           "names": NAMES}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({"verdict": verdict, "per_seed": per, "spread": spread,
                      "strata": {k: {kk: v[kk] for kk in ("n_snap", "pooled", "ci95")} for k, v in strata.items()}},
                     indent=1))


if __name__ == "__main__":
    main()
