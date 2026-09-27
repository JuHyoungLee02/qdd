"""Merge per-shard converter outputs (records_D/H.jsonl + report.json; frames stay in place) into one source dir:
concatenated records, summed counts, gate stats recomputed as row-weighted medians of the per-shard medians.
usage (pod): python -m xemb.dh_merge PARTS_DIR OUT_DIR"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np


def main(parts, out):
    os.makedirs(out, exist_ok=True)
    reps = []
    with open(os.path.join(out, "records_D.jsonl"), "w") as fD, open(os.path.join(out, "records_H.jsonl"), "w") as fH:
        for d in sorted(glob.glob(os.path.join(parts, "*"))):
            if not os.path.exists(os.path.join(d, "report.json")):
                continue
            reps.append(json.load(open(os.path.join(d, "report.json"))))
            for name, f in (("records_D.jsonl", fD), ("records_H.jsonl", fH)):
                f.writelines(open(os.path.join(d, name)))
    rep = {k: sum(r.get(k, 0) for r in reps) for k in ("episodes", "named", "states", "rows", "target_from_tcp")}
    rep["shards"] = len(reps)
    for key in ("g_unit_absdz_cm", "g_conv_cm"):
        rs = [r for r in reps if r.get(key)]
        w = np.array([max(1, r["states"]) for r in rs], float)
        rep[key] = {s: round(float(np.average([r[key][s] for r in rs], weights=w)), 2) for s in ("median", "p90", "le5cm")} \
            if rs else None
    json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
