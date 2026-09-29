"""prereg_marr §5 (outside the rule): reference errors for the aux trace head -- what a head that ignores the image
would score on the val labelled RB2 rows. Reference = the train-split mean of each point slot (u, v in 0..255) over
the labelled train rows that have that point. Error per kept point in head-image pixels (672 x 376), the same
formula as se2e_tracept.trace_px_errors.
  python tools/marr_real/trace_ref.py --labels RB2.tracept.jsonl --out JSON
"""
from __future__ import annotations

import argparse
import json

import numpy as np

W, H = 672, 376


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(x) for x in open(a.labels, encoding="utf-8")]
    tr = [r for r in rows if r["split"] == "train" and r["trace255"]]
    va = [r for r in rows if r["split"] == "val" and r["trace255"]]
    mean = []
    for i in range(5):
        pts = np.asarray([r["trace255"][i] for r in tr if len(r["trace255"]) > i], float)
        mean.append(pts.mean(0) if len(pts) else np.array([127.5, 127.5]))
    err, per, first, last = [], [[] for _ in range(5)], [], []
    for r in va:
        es = []
        for i, q in enumerate(r["trace255"]):
            d = (np.asarray(q, float) - mean[i]) / 255.0
            e = float(np.hypot(d[0] * (W - 1), d[1] * (H - 1)))
            es.append(e)
            per[i].append(e)
        err += es
        first.append(es[0])
        last.append(es[-1])
    out = {"n_train_rows": len(tr), "n_val_rows": len(va), "n_points": len(err),
           "train_mean_trace255": [[round(float(v), 2) for v in m] for m in mean],
           "mean_px": float(np.mean(err)), "median_px": float(np.median(err)),
           "per_point_mean_px": [float(np.mean(x)) if x else None for x in per],
           "first_point_mean_px": float(np.mean(first)), "end_point_mean_px": float(np.mean(last)),
           "end_point_median_px": float(np.median(last))}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
