"""A/A noise floor: the same training file with seed 0 vs seed 1 (only --seed differs), paired snapshot bootstrap of the
mean approach 3D difference per L8-X set (the +2 mm non-inferiority rule applied to two copies of one arm).
usage: python aa_check.py <eval dir seed 0> <eval dir seed 1> [...pairs]   -> one JSON line per pair"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import opratio_compare as OC  # noqa: E402

a = sys.argv[1:]
for d0, d1 in zip(a[::2], a[1::2]):
    out = {"s0": d0, "s1": d1}
    for xs in OC.XSETS:
        S = [{r["id"]: r for r in OC.jl(os.path.join(d, f"x_{xs}_d-min_clean", "scores.jsonl"))} for d in (d0, d1)]
        v = [S[1][k]["approach_3d_mm"] - S[0][k]["approach_3d_mm"] for k in S[0] if k in S[1]
             and S[0][k].get("approach_3d_mm") is not None and S[1][k].get("approach_3d_mm") is not None]
        ci = OC.boot(v)
        out[xs] = {"ci95": ci, "passes_2mm_both_ways": bool(ci[1] <= 2.0 and -ci[0] <= 2.0)}
    print(json.dumps(out))
