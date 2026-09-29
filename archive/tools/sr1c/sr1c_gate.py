"""E-SR1c gates (docs/stage3/prereg_sr1c.md §0). Each prints a JSON line with "pass".
  ga  C0_EVAL.jsonl                       authority estimate: |dist_hat - dist_priv| on snapshots with dist_priv in
                                          [4, 12] cm: median <= 1 cm, p90 <= 2.5 cm; near misclassification
                                          (a_priv = 0 and a_hat > 0) <= 5 %
  g0  TRAIN_LOG --n-registered N --batch B   branch rows joined = N +- 1 %, none missing; every training step's branch
                                          share n_branch / (n_branch + B) = 0.5 +- 0.02
  g1  C0_EVAL.jsonl SR0_C0.jsonl          C0 path reproduction: A_xy (all 1,200) = E-SR0's 0.43059 +- 0.005 and
                                          'pred' chunk displacement vs sr0 median <= 1 mm (the same noise seeds)
  g2  TRAIN_LOG --limit-s S               last step's elapsed <= S (2 x the E-MA2 run), no NaN loss
  cfg C0_TRAIN_LOG ARM_TRAIN_LOG          the arm's training arguments equal C0's except the E-SR1c options / names
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
SR0_A_XY = 0.43059  # docs/stage3/results/sr0.md §6 (recount 0.43059)
FREE_KEYS = ("run", "out_root", "cf_branch", "cf_frac", "dec_cond", "overwrite", "reload_check", "save_every")


def ga(snaps: list) -> dict:
    band = [s for s in snaps if s.get("dist_priv") is not None and 0.04 <= s["dist_priv"] <= 0.12]
    err = np.array([abs(s["dist_hat"] - s["dist_priv"]) for s in band])
    near = [s for s in snaps if s.get("a_priv") == 0.0]
    mis = [s for s in near if (s.get("a_hat") or 0.0) > 0.0]
    far = [s for s in snaps if s.get("a_priv") == 1.0]
    out = {"band_n": len(band), "err_median_m": float(np.median(err)) if len(err) else None,
           "err_p90_m": float(np.quantile(err, 0.9)) if len(err) else None, "near_n": len(near),
           "near_misclass": len(mis) / len(near) if near else None,
           "far_n": len(far), "far_a_hat_below_1": (sum((s.get("a_hat") or 0.0) < 1.0 for s in far) / len(far)
                                                     if far else None)}
    out["pass"] = bool(len(err) and out["err_median_m"] <= 0.01 + 1e-12 and out["err_p90_m"] <= 0.025 + 1e-12
                       and near and out["near_misclass"] <= 0.05 + 1e-12)
    return out


def g0(log: list, n_registered: int, batch: int) -> dict:
    j = [r for r in log if r.get("event") == "sr1c_branches"]
    steps = [r for r in log if r.get("event") == "train"]
    share = [r["n_branch"] / (r["n_branch"] + batch) for r in steps if "n_branch" in r]
    out = {"joined": j[-1]["joined"] if j else None, "missing": j[-1]["missing"] if j else None,
           "steps": len(steps), "steps_with_branch": len(share),
           "share_min": min(share) if share else None, "share_max": max(share) if share else None}
    out["pass"] = bool(j and abs(out["joined"] - n_registered) <= 0.01 * n_registered and out["missing"] == 0
                       and share and len(share) == len(steps) and abs(out["share_min"] - 0.5) <= 0.02
                       and abs(out["share_max"] - 0.5) <= 0.02)
    return out


def g2(log: list, limit_s: float) -> dict:
    steps = [r for r in log if r.get("event") == "train"]
    nan = sum(1 for r in steps if not math.isfinite(r.get("total", float("nan"))))
    el = steps[-1]["elapsed_s"] if steps else None
    return {"last_step": steps[-1]["step"] if steps else None, "elapsed_s": el, "nan": nan,
            "pass": bool(steps and el <= limit_s and nan == 0)}


def config_diff(c0: dict, c1: dict) -> dict:
    keys = (set(c0) | set(c1)) - set(FREE_KEYS)
    return {k: (c0.get(k), c1.get(k)) for k in sorted(keys) if c0.get(k) != c1.get(k)}


def g1(snaps: list, sr0: list) -> dict:
    spec = importlib.util.spec_from_file_location("sr0_verdict", os.path.join(_HERE, "..", "sr0", "sr0_verdict.py"))
    V0 = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))
    spec.loader.exec_module(V0)
    st = [V0.snap_stats(s, grip=True) for s in snaps]
    a = V0.pool([st], range(len(st)))["a_xy"]
    ref = {s["id"]: s for s in sr0}
    d = [1e3 * float(np.linalg.norm(np.subtract(s["c"]["pred"][:3], ref[s["id"]]["c"]["pred"][:3])))
         for s in snaps if s["id"] in ref]
    out = {"a_xy_all": a, "sr0_a_xy": SR0_A_XY, "n_matched": len(d),
           "pred_disp_diff_median_mm": float(np.median(d)) if d else None,
           "pred_disp_diff_max_mm": float(np.max(d)) if d else None}
    out["pass"] = bool(d and len(d) == len(snaps) and abs(a - SR0_A_XY) <= 0.005 + 1e-12
                       and out["pred_disp_diff_median_mm"] <= 1.0)
    return out


def _jsonl(path):
    return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip().startswith("{")]


def _snaps(path):
    return [r for r in _jsonl(path) if r.get("event") == "snap"]


def _args(path):
    return next(r for r in _jsonl(path) if r.get("event") == "config")["args"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("gate", choices=("ga", "g0", "g1", "g2", "cfg"))
    ap.add_argument("files", nargs="+")
    ap.add_argument("--n-registered", type=int, default=0)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--limit-s", type=float, default=4920.0)
    a = ap.parse_args(argv)
    if a.gate == "ga":
        r = ga(_snaps(a.files[0]))
    elif a.gate == "g0":
        r = g0(_jsonl(a.files[0]), a.n_registered, a.batch)
    elif a.gate == "g1":
        r = g1(_snaps(a.files[0]), _snaps(a.files[1]))
    elif a.gate == "g2":
        r = g2(_jsonl(a.files[0]), a.limit_s)
    else:
        diff = config_diff(_args(a.files[0]), _args(a.files[1]))
        r = {"diff": diff, "pass": not diff}
    print(json.dumps({"gate": a.gate, **r}), flush=True)
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
