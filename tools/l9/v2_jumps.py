"""L9 v2 diagnosis: where do measured joint steps exceed 0.04 rad (episode joints.npz) and what were the calls.
usage: python tools/l9/v2_jumps.py <episode dir>..."""
import json
import os
import sys

import numpy as np

for d in sys.argv[1:]:
    if not os.path.exists(os.path.join(d, "joints.npz")):
        print(d, "no joints.npz")
        continue
    z = np.load(os.path.join(d, "joints.npz"))
    print(d, {k: z[k].shape for k in z.files})
    meta = json.load(open(os.path.join(d, "meta.json")))
    q = z["q"][:, z["arm_ids"]] if "arm_ids" in z.files and len(z["arm_ids"]) else z["q"]
    names = [list(z["names"])[i] for i in z["arm_ids"]] if "arm_ids" in z.files else None
    dq = np.abs(np.diff(q, axis=0))
    t, j = np.unravel_index(np.argmax(dq), dq.shape)
    print("  max", round(float(dq.max()), 4), "step", int(t), "joint", names[j] if names is not None else j,
          "n_steps", len(q), "success", meta["success"], meta["end_reason"])
    bad = np.flatnonzero(dq.max(1) > 0.04)
    print("  steps > 0.04:", bad[:20].tolist(), "count", len(bad))
    gv = meta.get("grasp_v2") or {}
    for p in gv.get("picks", []):
        print("  pick", p.get("family"), p.get("part"), p.get("label_rule"), p.get("rule_step"), "n_valid",
              p.get("n_valid"), "timeline", json.dumps(p.get("timeline"))[:400])
