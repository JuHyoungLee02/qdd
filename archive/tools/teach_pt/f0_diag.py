"""E-PT F0 diagnosis: per zero-shot reply, the pointed pixel vs the label pixel, where the point lands (target object /
other object / table / robot), the chosen height intent vs the label's, and a systematic offset (median dx, dy px) --
to tell pointing error from intent error and from a coordinate-convention mismatch.
usage: python f0_diag.py <data jsonl> <eval dir> [n1000|px]"""
import collections
import json
import os
import sys

import numpy as np

from harvest.teach_pt import metrics as M
from harvest.teach_pt.evaluate import rescale

data, ev = sys.argv[1], sys.argv[2]
coords = sys.argv[3] if len(sys.argv) > 3 else "n1000"
rows = {json.loads(x)["id"]: json.loads(x) for x in open(data)}
reps = [json.loads(x) for x in open(os.path.join(ev, "replies.jsonl"))]
dx, dy, lands, intent, modes = [], [], collections.Counter(), collections.Counter(), collections.Counter()
ex = []
for rp in reps:
    r = rows.get(rp["id"])
    if r is None or r["kind"] != "control":
        continue
    p, _ = M.validate(rescale(rp["text"], coords), "pt")
    if p is None:
        modes["invalid"] += 1
        continue
    c = p["command"]
    modes[c["mode"]] += 1
    lab = json.loads(r["answer"])["command"]
    if c["mode"] == "point" and lab.get("point_2d") and c.get("point_2d"):
        dx.append((c["point_2d"][0] - lab["point_2d"][0]) * 0.672)
        dy.append((c["point_2d"][1] - lab["point_2d"][1]) * 0.376)
        intent[(lab["height"], c["height"])] += 1
        if len(ex) < 6:
            ex.append({"id": r["id"], "step": r["step"], "pred": c["point_2d"], "label": lab["point_2d"],
                       "h": [lab["height"], c["height"]]})
print(json.dumps({"modes": modes, "n_pairs": len(dx), "dx_px_median": round(float(np.median(dx)), 1) if dx else None,
                  "dy_px_median": round(float(np.median(dy)), 1) if dy else None,
                  "abs_dx_median": round(float(np.median(np.abs(dx))), 1) if dx else None,
                  "abs_dy_median": round(float(np.median(np.abs(dy))), 1) if dy else None,
                  "intent_label_vs_pred": {f"{a}->{b}": n for (a, b), n in intent.most_common(12)}, "examples": ex}))
