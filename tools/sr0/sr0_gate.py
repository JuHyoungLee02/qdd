"""E-SR0 path gate G1 (docs/stage3/prereg_sr0.md §4): sr0_eval must reproduce earlier evaluations of the same
checkpoints before its counterfactual conditions are read.
  se2e: predicted decisions = the E-MA3 baseline chunk_eval item predictions (>= 99 % of (key, question)) and the mean
        normalized chunk MSE under 'true' within 10 % of that run's sample_mse_norm (different noise draws)
  r2:   predicted decisions = the E-MA2 ma2eval c0 'none' predictions (>= 99 %) and the chunk under 'pred' (same noise
        seed and snapshot order as ma2eval) has median |disp - disp_ma2| <= 1 mm
Only the snapshots present in the sr0 file are compared (dry runs use a prefix).
  python tools/sr0/sr0_gate.py se2e SR0.jsonl MA3_CHUNK.jsonl | r2 SR0.jsonl MA2_EVAL.jsonl
"""
from __future__ import annotations

import json
import sys

import numpy as np

PRED_MIN, MSE_REL_MAX, DISP_MAX_M = 0.99, 0.10, 1e-3


def _read(path):
    return [json.loads(x) for x in open(path, encoding="utf-8")]


def _snaps(path):
    return [r for r in _read(path) if r.get("event") == "snap"]


def gate_se2e(sr0: str, ref: str) -> dict:
    snaps, recs = _snaps(sr0), _read(ref)
    items = {(r["key"], r["question"]): r["pred"] for r in recs if r.get("event") == "item"}
    summ = next((r for r in recs if r.get("event") == "summary"), None)
    pairs = [(p, items.get((s["key"], q))) for s in snaps for q, p in s["preds"].items()]
    if not pairs or summ is None or any(r is None for _, r in pairs):
        raise SystemExit("se2e gate: reference items / summary missing")
    agree = float(np.mean([p == r for p, r in pairs]))
    rel = float(np.mean([s["c"]["true"][5] for s in snaps]) / summ["sample_mse_norm"] - 1)
    return {"n_snap": len(snaps), "n_items": len(pairs), "pred_agree": agree, "mse_rel": rel,
            "pass": agree >= PRED_MIN and abs(rel) <= MSE_REL_MAX + 1e-12}


def gate_r2(sr0: str, ref: str) -> dict:
    snaps = _snaps(sr0)
    ev = {r["id"]: r for r in _read(ref) if r.get("event") == "item" and r.get("cond") == "none"}
    if not snaps or any(s["id"] not in ev for s in snaps):
        raise SystemExit("r2 gate: reference 'none' records missing")
    pairs = [(p, ev[s["id"]]["preds"].get(q)) for s in snaps for q, p in s["preds"].items()]
    agree = float(np.mean([p == r for p, r in pairs]))
    dd = [float(np.linalg.norm(np.asarray(s["c"]["pred"][:3]) - np.asarray(ev[s["id"]]["disp"]))) for s in snaps]
    med = float(np.median(dd))
    return {"n_snap": len(snaps), "n_items": len(pairs), "pred_agree": agree, "disp_diff_median_m": med,
            "disp_diff_max_m": float(np.max(dd)), "pass": agree >= PRED_MIN and med <= DISP_MAX_M + 1e-12}


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    r = {"se2e": gate_se2e, "r2": gate_r2}[a[0]](a[1], a[2])
    print(json.dumps(r))
    sys.exit(0 if r["pass"] else 3)


if __name__ == "__main__":
    main()
