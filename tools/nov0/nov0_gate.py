"""E-NOV0 path gate G1 (docs/stage3/prereg_nov0.md §4). Our eval-split records against the same checkpoint's
earlier records on the overlapping ids (E-MA2 eval set 1,200):
  decisions  predicted option per (id, question) == E-MA2 eval_c0.jsonl cond 'none' preds, share >= 0.99
  chunk MSE  the same flow-noise draws (nov0_extract --noise-ref = E-SR0 numbering): mean of our pred-decision chunk
             MSE / mean of E-SR0 sr0_c0.jsonl 'pred' MSE within 1 +- 0.02 and median per-snapshot relative
             difference <= 0.01 (batched bf16 numerics only)
  python tools/nov0/nov0_gate.py OUR_EVAL_META MA2_EVAL_C0 SR0_C0 > gate.json   (exit 1 when failing)
"""
from __future__ import annotations

import json
import sys


def gate_g1(ours, ma2_items, sr0_snaps, min_agree: float = 0.99, mse_tol: float = 0.02,
            med_tol: float = 0.01) -> dict:
    ref = {r["id"]: r["preds"] for r in ma2_items if r.get("event") == "item" and r.get("cond") == "none"}
    sr = {r["id"]: r["c"]["pred"][5] for r in sr0_snaps if r.get("event") == "snap"}
    ov = [o for o in ours if o["id"] in ref and o["id"] in sr]
    n_q = n_eq = 0
    for o in ov:
        for q, p in ref[o["id"]].items():
            n_q += 1
            n_eq += o["preds"].get(q) == p
    agree = n_eq / n_q if n_q else 0.0
    ratio = (sum(o["mse"] for o in ov) / sum(sr[o["id"]] for o in ov)) if ov else float("nan")
    rel = sorted(abs(o["mse"] - sr[o["id"]]) / max(sr[o["id"]], 1e-12) for o in ov)
    med = rel[len(rel) // 2] if rel else float("nan")
    ok = bool(ov) and agree >= min_agree and abs(ratio - 1.0) <= mse_tol and med <= med_tol
    return {"pass": ok, "n_overlap": len(ov), "agree": agree, "n_q": n_q, "mse_ratio": ratio, "mse_med_rel": med}


def _jl(p):
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    ours = [m for m in _jl(a[0]) if m.get("event") != "summary"]
    r = gate_g1(ours, _jl(a[1]), _jl(a[2]))
    print(json.dumps(r))
    sys.exit(0 if r["pass"] else 1)


if __name__ == "__main__":
    main()
