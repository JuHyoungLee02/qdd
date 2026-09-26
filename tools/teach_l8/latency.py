"""Per-call latency (median, p95) and tokens of closed-loop astra-solo results under a root, and of an offline eval
replies.jsonl. usage: python latency.py <closed arm root> [<replies.jsonl> ...]"""
import glob
import json
import os
import sys

import numpy as np

lat, tin, tout = [], [], []
for p in glob.glob(os.path.join(sys.argv[1], "*", "*", "s*", "result.json")):
    r = json.load(open(p))
    for c in r["calls"]:
        if not c.get("api_error"):
            lat.append(c["latency_s"])
            u = c.get("usage") or {}
            tin.append(u.get("input_tokens") or 0)
            tout.append(u.get("output_tokens") or 0)
print(json.dumps({"closed_calls": len(lat), "latency_p50": round(float(np.median(lat)), 2),
                  "latency_p95": round(float(np.percentile(lat, 95)), 2), "tokens_in_median": float(np.median(tin)),
                  "tokens_out_median": float(np.median(tout))}))
for f in sys.argv[2:]:
    L = [json.loads(x) for x in open(f)]
    v = [d["latency_s"] for d in L if d.get("latency_s") is not None]
    print(json.dumps({"replies": f, "n": len(v), "latency_p50": round(float(np.median(v)), 2),
                      "note": "8 concurrent workers (offline)"}))
