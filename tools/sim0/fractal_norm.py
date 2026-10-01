"""E-SIM0 arm B: openpi norm_stats.json for pi05_base on the Google Robot from Octo's public fractal action statistics
(rail-berkeley/octo-base-1.5 dataset_statistics.json, MIT): actions mean / std as given; q01 / q99 (pi05 quantile
normalisation) = mean -+ 2.326 std clipped to min / max (Octo publishes no quantiles: an approximation, prereg change 1);
state (8 dims, unused by pi05 without discrete state input) mean 0 / std 1 / q -1..1.
usage: fractal_norm.py <octo stats json> <out dir: .../assets/physical-intelligence/libero> [dataset key]"""
import json
import os
import sys

import numpy as np

key = sys.argv[3] if len(sys.argv) > 3 else "fractal20220817_data"  # E-SIM1: bridge_dataset
d = json.load(open(sys.argv[1]))[key]["action"]
m, s = np.array(d["mean"]), np.array(d["std"])
q01 = np.maximum(m - 2.326 * s, np.array(d["min"]))
q99 = np.minimum(m + 2.326 * s, np.array(d["max"]))
ns = {"norm_stats": {"state": {"mean": [0.0] * 8, "std": [1.0] * 8, "q01": [-1.0] * 8, "q99": [1.0] * 8},
                     "actions": {"mean": m.tolist(), "std": s.tolist(), "q01": q01.tolist(), "q99": q99.tolist()}}}
os.makedirs(sys.argv[2], exist_ok=True)
json.dump(ns, open(os.path.join(sys.argv[2], "norm_stats.json"), "w"), indent=1)
print(json.dumps(ns["norm_stats"]["actions"]))
