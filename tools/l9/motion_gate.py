"""L9 §10 motion gate: yield and joint steps of the human-like motion pilot against the baseline pilot on the same
task definitions, plus TCP path statistics (tcp_path of result.json): mean speed while moving, peak / mean speed,
direction change per cm moved (curvature proxy), share of time still. usage:
  python tools/l9/motion_gate.py <motion collect root> <baseline collect root>... --out report.json"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

out = sys.argv[sys.argv.index("--out") + 1]
roots = [a for a in sys.argv[1:] if not a.startswith("--") and a != out]
motion_root, base_roots = roots[0], roots[1:]


def path_stats(path):
    P = np.asarray(path, float)
    if len(P) < 5:
        return None
    t, X = P[:, 0], P[:, 1:4]
    dt = np.diff(t)
    dt[dt <= 0] = 1e-3
    v = np.diff(X, axis=0) / dt[:, None]
    sp = np.linalg.norm(v, axis=1)
    mov = sp > 0.02
    if mov.sum() < 3:
        return None
    u = v[mov] / sp[mov][:, None]
    ang = np.arccos(np.clip((u[1:] * u[:-1]).sum(1), -1, 1))
    dist = float((sp[mov] * dt[mov]).sum())
    return {"mean_speed": float(sp[mov].mean()), "peak_over_mean": float(sp[mov].max() / sp[mov].mean()),
            "turn_deg_per_cm": float(np.degrees(ang.sum()) / max(dist * 100, 1e-6)), "still_share": float(1 - mov.mean())}


def scan(root, defs=None):
    res = defaultdict(lambda: [0, 0])
    stats, jumps, n = [], 0, 0
    for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
        meta = json.load(open(m))
        if meta.get("gen") != "l9" or (defs is not None and meta["task_id"] not in defs):
            continue
        ok = bool(meta["success"]) and (meta.get("max_dq_rad") or 0) <= 0.04
        res[meta["task_id"]][0] += 1
        res[meta["task_id"]][1] += ok
        jumps += (meta.get("max_dq_rad") or 0) > 0.04
        n += 1
        rp = os.path.join(os.path.dirname(m), "result.json")
        if os.path.exists(rp):
            s = path_stats(json.load(open(rp)).get("tcp_path") or [])
            if s:
                stats.append(s)
    agg = {k: round(float(np.median([s[k] for s in stats])), 4) for k in (stats[0] if stats else {})}
    spread = {k: [round(float(np.percentile([s[k] for s in stats], q)), 4) for q in (10, 90)] for k in (stats[0] if stats else {})}
    return {"n": n, "ok": sum(v[1] for v in res.values()), "jumps": jumps, "per_def": {k: v for k, v in res.items()},
            "path_median": agg, "path_p10_p90": spread}


mo = scan(motion_root)
defs = set(mo["per_def"])
ba = {"n": 0, "ok": 0, "jumps": 0}
bas = [scan(r, defs) for r in base_roots]
base = {"n": sum(b["n"] for b in bas), "ok": sum(b["ok"] for b in bas), "jumps": sum(b["jumps"] for b in bas),
        "path_median": bas[0]["path_median"] if bas else {}, "path_p10_p90": bas[0]["path_p10_p90"] if bas else {}}
rep = {"motion": {k: mo[k] for k in ("n", "ok", "jumps", "path_median", "path_p10_p90")},
       "baseline": base,
       "yield_motion": round(mo["ok"] / max(mo["n"], 1), 3), "yield_baseline": round(base["ok"] / max(base["n"], 1), 3)}
rep["jump_rate_motion"] = round(mo["jumps"] / max(mo["n"], 1), 3)
rep["jump_rate_baseline"] = round(base["jumps"] / max(base["n"], 1), 3)
# jumps (> 0.04 rad) also happen in the baseline (contact on joint 7) and such episodes are never built: the gate is
# "not more often than the baseline" (+2 %p) and a yield within 5 %p of the baseline on the same definitions
rep["pass"] = bool(rep["jump_rate_motion"] <= rep["jump_rate_baseline"] + 0.02
                   and rep["yield_motion"] >= rep["yield_baseline"] - 0.05)
json.dump(rep, open(out, "w"), indent=1)
print(json.dumps(rep))
