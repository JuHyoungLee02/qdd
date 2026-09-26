"""C' pool size vs the top-down threshold (30 / 45 / 60 deg) per source, from the converters' gates.json.
usage: cpool.py"""
import json
import numpy as np

X = "/data/harvest/out/xemb_proto"
out = {}
for name, path, key in (("franka", f"{X}/mbfranka/gates.json", "grasp_tilt_deg"),
                        ("rby1", f"{X}/molmobot50/gates.json", "grasp_tilt_deg"),
                        ("robotwin", f"{X}/robotwin2/gates.json", "grasp_tilt_deg")):
    g = json.load(open(path))
    eps = g["per_episode"]
    t = np.array([e[key] for e in eps if e.get(key) is not None], float)
    n_c = np.array([e.get("n_C", 0) for e in eps if e.get(key) is not None], float)
    cand = g.get("n_C_without_topdown_filter") or n_c.sum()
    per_ep = cand / max(1, len(t))
    out[name] = {"grasps": int(len(t)), **{f"le{a}": round(float((t <= a).mean()), 3) for a in (30, 45, 60)},
                 **{f"C_rows_le{a}_est": int(round(float((t <= a).sum()) * per_ep)) for a in (30, 45, 60)}}
print(json.dumps(out, indent=1))
