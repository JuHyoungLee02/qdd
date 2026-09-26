"""E-SR1b gates (docs/stage3/prereg_sr1b.md §0 / §4), read before any arm's adherence value.

  repro NEW_W1.jsonl SR0_C0.jsonl MA2_EVAL_C0.jsonl
      sr1b_eval at w = 1 on the E-MA2 C0 checkpoint must reproduce E-SR0's evaluation of it: predicted decisions agree
      >= 99 % (snapshot, question), median |disp - disp_sr0| over every condition <= 0.01 mm, |A_xy - A_xy_sr0|
      <= 0.005 (sr0_verdict functions), and the decision accuracy (items, prediction in target set) within 0.002 of
      the E-MA2 'none' evaluation of the same checkpoint. Only snapshots present in NEW are compared (dry runs).
  train LOG.jsonl OUT_FILE [--relabel] [--max-min 90]
      a training run: n_train + n_val = 151,870, no non-finite training loss, validation 'dec' at step >= 500 not above
      step 0, every eval present, wall time <= --max-min (2x the expected 45 min), and with --relabel the
      'sr1b_relabel' event with n = 151,870 and missing 0 (the relabel event is printed to OUT_FILE, the stdout copy).
Exit 0 = pass, 3 = fail; one JSON line on stdout.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))

import sr0_verdict as V0  # noqa: E402

PRED_MIN, DISP_MAX_M, AXY_MAX, ACC_MAX = 0.99, 1e-5, 0.005, 0.002
N_ROWS = 151870


def _read(path):
    return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]


def _snaps(path):
    return [r for r in _read(path) if r.get("event") == "snap"]


def _a_xy(snaps):
    st = [V0.snap_stats(x, True) for x in snaps]
    return V0.pool([st], np.arange(len(st)))["a_xy"]


def gate_repro(new: str, sr0: str, ma2: str) -> dict:
    a = _snaps(new)
    ref = {s["id"]: s for s in _snaps(sr0)}
    ev = {r["id"]: r for r in _read(ma2) if r.get("event") == "item" and r.get("cond") == "none"}
    if not a or any(s["id"] not in ref or s["id"] not in ev for s in a):
        raise SystemExit("repro gate: reference records missing")
    b = [ref[s["id"]] for s in a]
    agree = float(np.mean([p == r["preds"].get(q) for s, r in zip(a, b) for q, p in s["preds"].items()]))
    dd = [float(np.linalg.norm(np.asarray(s["c"][n][:3]) - np.asarray(r["c"][n][:3])))
          for s, r in zip(a, b) for n in s["c"]]
    acc_new = float(np.mean([s["preds"].get(q) in tg for s in a for q, tg in s["targets"].items()]))
    acc_ma2 = float(np.mean([ev[s["id"]]["preds"].get(q) in tg for s in a
                             for q, tg in ev[s["id"]]["targets"].items()]))
    ax_new, ax_ref = _a_xy(a), _a_xy(b)
    return {"n_snap": len(a), "pred_agree": agree, "disp_diff_median_m": float(np.median(dd)),
            "disp_diff_max_m": float(np.max(dd)), "a_xy_new": ax_new, "a_xy_sr0": ax_ref, "acc_new": acc_new,
            "acc_ma2": acc_ma2,
            "pass": agree >= PRED_MIN and float(np.median(dd)) <= DISP_MAX_M + 1e-12
            and abs(ax_new - ax_ref) <= AXY_MAX + 1e-12 and abs(acc_new - acc_ma2) <= ACC_MAX + 1e-12}


def gate_train(log: str, out_file: str, relabel: bool, max_min: float = 90.0, n_rows: int = N_ROWS) -> dict:
    recs = _read(log)
    cfg = next((r for r in recs if r.get("event") == "config"), None)
    tr = [r for r in recs if r.get("event") == "train"]
    ev = {r["step"]: r for r in recs if r.get("event") == "eval"}
    if cfg is None or not tr:
        raise SystemExit(f"{log}: config / train records missing")
    total = cfg["total_steps"]
    nonfinite = sum(1 for r in tr if not math.isfinite(r.get("total", float("nan"))))
    steps = sorted(ev)
    want = sorted({0, total} | set(range(cfg["args"]["eval_every"], total + 1, cfg["args"]["eval_every"])))
    dec0 = ev.get(0, {}).get("dec")
    later = [ev[s]["dec"] for s in steps if s >= 500]
    wall_min = tr[-1]["elapsed_s"] / 60.0
    r = {"n_train": cfg["n_train"], "n_val": cfg["n_val"], "steps": tr[-1]["step"], "total_steps": total,
         "nonfinite": nonfinite, "eval_steps": steps, "dec0": dec0, "dec_later_max": max(later) if later else None,
         "wall_min": round(wall_min, 1), "prompt_sha": cfg["prompt_config"].get("sha"),
         "sr1b": {k: cfg["prompt_config"].get(k) for k in ("sr1b", "sr1b_drop", "sr1b_relabel")}}
    ok = (cfg["n_train"] + cfg["n_val"] == n_rows and nonfinite == 0 and tr[-1]["step"] == total and steps == want
          and dec0 is not None and all(d <= dec0 for d in later) and wall_min <= max_min)
    if relabel:
        ev_r = [json.loads(x) for x in open(out_file, encoding="utf-8", errors="replace")
                if x.startswith('{"event": "sr1b_relabel"')]
        r["relabel"] = ev_r[-1] if ev_r else None
        ok = ok and bool(ev_r) and ev_r[-1]["n"] == n_rows and ev_r[-1]["missing"] == 0
    r["pass"] = bool(ok)
    return r


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if a[0] == "repro":
        r = gate_repro(a[1], a[2], a[3])
    elif a[0] == "train":
        mm = float(a[a.index("--max-min") + 1]) if "--max-min" in a else 90.0
        nr = int(a[a.index("--n-rows") + 1]) if "--n-rows" in a else N_ROWS
        r = gate_train(a[1], a[2], "--relabel" in a, mm, nr)
    else:
        raise SystemExit("usage: sr1b_gate.py repro NEW SR0 MA2 | train LOG OUT [--relabel] [--max-min M]")
    print(json.dumps(r))
    sys.exit(0 if r["pass"] else 3)


if __name__ == "__main__":
    main()
