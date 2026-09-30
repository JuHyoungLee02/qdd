"""L9 failure anatomy over a collect root (pure): per failed episode the dominant stuck step (the step label that
repeats most), whether the arm jumped (> 0.04 rad), the result flags (collision / knocked / tipped / off_table), the
carry height gap (carry target z - reached TCP z while carrying) and the scene lift / surface height.
usage: python tools/l9/failstats.py <collect root> [--def ID]"""
import glob
import json
import os
import sys
from collections import Counter

import numpy as np

root = sys.argv[1]
only = sys.argv[sys.argv.index("--def") + 1] if "--def" in sys.argv else None
stuck, flags, gaps, jumps, n = Counter(), Counter(), [], 0, 0
by_def = {}
for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
    meta = json.load(open(m))
    if meta.get("gen") != "l9" or meta.get("success") or (only and meta.get("task_id") != only):
        continue
    d = os.path.dirname(m)
    n += 1
    rows = [json.loads(x) for x in open(os.path.join(d, "labels.jsonl"))]
    c = Counter(r["step"] for r in rows)
    top = c.most_common(1)[0][0] if c else "none"
    stuck[top] += 1
    res = json.load(open(os.path.join(d, "result.json")))
    for k in ("collision", "tipped", "off_table"):
        flags[k] += bool(res.get(k))
    flags["knocked"] += bool(res.get("knocked"))
    j = (meta.get("max_dq_rad") or 0) > 0.04
    jumps += j
    carry = [r for r in rows if r["step"] == "carry_up"]
    if carry:
        tz = float(meta["table_z"])
        gaps.append(round(tz + 0.22 - float(carry[-1]["gt"]["tcp"][2]), 3))
    by_def.setdefault(meta["task_id"], Counter())[top] += 1
print(json.dumps({"failed": n, "stuck_step": dict(stuck), "flags": dict(flags), "arm_jump": jumps,
                  "carry_gap_m_median": float(np.median(gaps)) if gaps else None, "n_carry_stuck": len(gaps)}))
for k, v in sorted(by_def.items()):
    print(k, dict(v))
