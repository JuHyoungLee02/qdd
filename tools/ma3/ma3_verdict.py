"""prereg_ma3 §5 verdict (fixed before any kv run): runs (none, kv) x seeds 1, 2 on se2e_c1 with the motion line;
none_s1 / none_s2 = the motion-confirm checkpoints motion_s1 / motion_s2 (reuse checked bit for bit).

Inputs: per run tools/ma3/chunk_eval.py's jsonl on the FULL val set (1,799 snapshots: item + chunk records), the
transition flags and tools/ma3/ma3_latency.py's json.
  python tools/ma3/ma3_verdict.py --pred none_s1=F kv_s1=F none_s2=F kv_s2=F --trans F --lat F --out JSON
Primary: expert chunk error = per-snapshot normalized masked MSE of the chunk sampled (10 Euler steps, fixed noise)
conditioned on the committed decisions (evaluate()'s sample_mse_norm). r_s = 1 - mean(kv_s) / mean(none_s),
pooled = mean over seeds. ADOPT iff pooled r >= MIN_REL (0.05) AND its bootstrap 2.5 % bound > 0 AND the pooled
decision accuracy effect's bootstrap 2.5 % bound >= -0.01 (non-inferiority) AND FULL (decide + chunk) p95
kv / base - 1 <= 0.10. CMP_EPS 1e-12 on thresholds; the chunk bound strictly > 0. Reported outside the rule: the
predicted-decision chunk error, arm MAE (rad), fixed-noise flow loss, accuracy per stratum / source, spreads.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "se2e"))
import paired_verdict as PV  # noqa: E402

ARM = "kv"
MIN_REL, ACC_MARGIN, MAX_P95_INC = 0.05, 0.01, 0.10


def rule(rel, rel_lower, acc_lower, p95_ratio) -> dict:
    c = {"c_rel": PV.ge(rel, MIN_REL), "c_rel_lower": rel_lower > 0, "c_acc_noninf": PV.ge(acc_lower, -ACC_MARGIN),
         "c_latency": PV.le(p95_ratio - 1.0, MAX_P95_INC)}
    return {**{k: bool(v) for k, v in c.items()}, "adopt": bool(all(c.values()))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", nargs=4, required=True)
    ap.add_argument("--trans", required=True)
    ap.add_argument("--lat", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-snap", type=int, default=1799)
    a = ap.parse_args()
    paths = dict(x.split("=", 1) for x in a.pred)
    flags = json.load(open(a.trans))["flags"]
    items, m = PV.load_runs(paths, flags, ARM, a.n_snap)
    ch = {c: PV.load_chunks(p) for c, p in paths.items()}
    for c in ch:
        assert sorted(ch[c]) == sorted({r["key"] for r in items[c]}), f"{c}: chunk keys != item keys"
        s = m[c]["summary"]
        if s is not None:
            assert abs(sum(r["mse_n"] for r in ch[c].values()) / len(ch[c]) - s["sample_mse_norm"]) < 1e-12, c
    prim = PV.rel_reduction(ch, ARM, "mse_n")
    extra = {f: PV.rel_reduction(ch, ARM, f) for f in ("mse_pred", "mae_q", "fm")}
    per, pooled, spread = PV.effects(m, ARM)
    boot = PV.bootstrap_acc(items, flags, ARM)
    lat = json.load(open(a.lat))
    ratio = lat["arms"]["kv"]["full_p95"] / lat["arms"]["base"]["full_p95"]
    v = {"pooled_rel_reduction": prim["pooled"], "rel_lower_95": prim["boot_95"][0],
         "acc_pooled": pooled["all"], "acc_lower_95": boot["all"][0], "full_p95_ratio": ratio,
         **rule(prim["pooled"], prim["boot_95"][0], boot["all"][0], ratio)}
    out = {"chunk_primary": prim, "chunk_extra": extra,
           "runs": {c: {k: x for k, x in r.items() if k != "summary"} for c, r in m.items()},
           "summaries": {c: r["summary"] for c, r in m.items()}, "acc_per_seed_effect": per,
           "acc_pooled_effect": pooled, "acc_seed_spread": spread, "acc_bootstrap_95": boot,
           "per_source_pooled": PV.source_effects(m, ARM), "latency": lat, "verdict": v,
           "rule": {"min_rel": MIN_REL, "rel_lower_gt": 0.0, "acc_lower_ge": -ACC_MARGIN,
                    "max_p95_increase": MAX_P95_INC, "n_boot": PV.N_BOOT, "seed": PV.SEED, "cmp_eps": PV.CMP_EPS}}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({"verdict": v, "chunk": prim, "acc_per_seed": per}, indent=1))


if __name__ == "__main__":
    main()
