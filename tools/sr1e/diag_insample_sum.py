"""Summaries of tools/sr1e/diag_insample.py outputs (D1): far A_xy / A_z / rho / true-direction hit / chunk MSE on the
TRAIN snapshots, split by whether the E-SR1d run drew a branch of that snapshot.
  python tools/sr1e/diag_insample_sum.py NAME=EVAL.jsonl:TAGS.json ... > sum.json
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))
_spec = importlib.util.spec_from_file_location("sr0_verdict", os.path.join(_HERE, "..", "sr0", "sr0_verdict.py"))
V0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V0)
KEYS = ("a_xy", "a_z", "rho_mean", "true_rate", "mse_true", "sens_mm_median", "mean_cos_xy")


def summ(sel):
    if not sel:
        return {"n": 0}
    p = V0.pool([sel], range(len(sel)))
    return {"n": len(sel), **{k: round(float(p[k]), 4) for k in KEYS if k in p}}


def main():
    out = {}
    for arg in sys.argv[1:]:
        name, rest = arg.split("=", 1)
        ev, tg = rest.split(":")
        tags = json.load(open(tg))["draws"]
        st = [V0.snap_stats(json.loads(x), False) for x in open(ev, encoding="utf-8") if '"event": "snap"' in x]
        out[name] = {"all": summ(st), "drawn": summ([x for x in st if tags.get(x["key"], 0) > 0]),
                     "not_drawn": summ([x for x in st if tags.get(x["key"], 0) == 0])}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
