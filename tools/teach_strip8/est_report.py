"""E-PRIV8 M1-keep estimate errors (table_z, obj_h) per evaluation set and their Spearman correlation with the
approach z error (|goal z - label z| of approach rows). usage: python est_report.py <eval_priv dir> <data_priv dir>"""
import json
import os
import sys

import numpy as np

from harvest.astra_motion.schema import SchemaError, extract_json
from harvest.teach_strip8 import priv as P

ev, dp = sys.argv[1], sys.argv[2]
for k in ("dev_x", "ood_hx", "dev", "ood_h"):
    d = os.path.join(ev, f"{k}_m1-keep")
    if not os.path.exists(os.path.join(d, "replies.jsonl")):
        continue
    rows = [json.loads(x) for x in open(os.path.join(dp, f"ev_{k}", "dev_m1.jsonl"))]
    rep = {}
    for x in open(os.path.join(d, "replies.jsonl")):
        q = json.loads(x)
        rep[q["id"]] = q
    out = P.est_errors(rows, rep)
    sc = {s["id"]: s for s in (json.loads(x) for x in open(os.path.join(d, "scores.jsonl")))}
    a, b = [], []
    for r in rows:
        s = sc.get(r["id"])
        if r["kind"] != "control" or not s or s.get("approach_3d_mm") is None:
            continue
        try:
            e = extract_json(rep[r["id"]]["text"])["estimates"]
            a.append(abs(float(e["table_z"]) - r["est"]["table_z"]))
            g = json.loads(r["answer"])["command"]
            b.append(s["approach_3d_mm"])
        except (SchemaError, KeyError, TypeError, ValueError):
            continue
    if len(a) > 5:
        ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
        out["spearman_tablez_vs_3d"] = round(float(np.corrcoef(ra, rb)[0, 1]), 3)
        out["n_corr"] = len(a)
    print(k, json.dumps(out))
