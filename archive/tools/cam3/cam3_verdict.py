"""prereg_cam3 §5 verdict (fixed before any cam3 run): runs (none, cam3) x seeds 1, 2 on se2e_c1 with the motion
line; none_s1 / none_s2 = the motion-confirm checkpoints motion_s1 / motion_s2 (reuse checked bit for bit).

Inputs: per run the `predict` jsonl of its last/ checkpoint on the FULL val set (1,799 snapshots), the transition
flags (se2e_c1/transition_val.json) and tools/cam3/cam3_latency.py's json.
  python tools/cam3/cam3_verdict.py --pred none_s1=F cam3_s1=F none_s2=F cam3_s2=F --trans F --lat F --out JSON
ADOPT iff pooled overall accuracy effect >= +0.02 AND its bootstrap 2.5 % bound > 0 AND pooled transition-stratum
effect >= -0.01 AND FULL decide p95 (cam3 / cam2) - 1 <= 0.10 (CMP_EPS 1e-12 on thresholds; the bound strictly
> 0). Reported outside the rule: NLL, steady stratum, per question, per source, seed spread, GPU p95, tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "se2e"))
import paired_verdict as PV  # noqa: E402

ARM = "cam3"
MIN_GAIN, MAX_TRANS_DROP, MAX_P95_INC = 0.02, 0.01, 0.10


def rule(pooled, lower, trans, p95_ratio) -> dict:
    c = {"c_point": PV.ge(pooled, MIN_GAIN), "c_lower": lower > 0, "c_transition": PV.ge(trans, -MAX_TRANS_DROP),
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
    per, pooled, spread = PV.effects(m, ARM)
    _, pooled_nll, _ = PV.effects(m, ARM, "nll")
    boot = PV.bootstrap_acc(items, flags, ARM)
    lat = json.load(open(a.lat))
    ratio = lat["formats"]["cam3"]["full_p95"] / lat["formats"]["cam2"]["full_p95"]
    v = {"pooled_overall": pooled["all"], "lower_95": boot["all"][0], "pooled_transition": pooled["transition"],
         "full_p95_ratio": ratio, **rule(pooled["all"], boot["all"][0], pooled["transition"], ratio)}
    out = {"runs": {c: {k: x for k, x in r.items() if k != "summary"} for c, r in m.items()}, "per_seed_effect": per,
           "pooled_effect": pooled, "seed_spread": spread, "pooled_effect_nll": pooled_nll,
           "per_source_pooled": PV.source_effects(m, ARM), "bootstrap_95": boot, "latency": lat, "verdict": v,
           "rule": {"min_gain": MIN_GAIN, "lower_bound_gt": 0.0, "max_transition_drop": MAX_TRANS_DROP,
                    "max_p95_increase": MAX_P95_INC, "n_boot": PV.N_BOOT, "seed": PV.SEED, "cmp_eps": PV.CMP_EPS}}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({"verdict": v, "per_seed": per, "spread": spread, "per_source": out["per_source_pooled"]},
                     indent=1))


if __name__ == "__main__":
    main()
