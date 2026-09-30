import json, glob, math, collections
import numpy as np
R = "/data/harvest/out/couple/cj1/res/ov"
def dvec(s):
    if s in (None, "none"): return None
    p = s.split("_"); v = np.zeros(2)
    for i in range(0, len(p) - 1, 2):
        v[0 if p[i+1] == "x" else 1] += 1 if p[i] == "plus" else -1
    n = np.linalg.norm(v); return v / n if n else None
ang = collections.defaultdict(list); goalang = []
for f in glob.glob(R + "/*/s*/vla_steps.jsonl"):
    rows = [json.loads(l) for l in open(f)]
    for a, b in zip(rows, rows[1:]):
        if a.get("chunk") is None: continue
        d = dvec(a["dec"]["dir_xy"]); mv = np.array(b["tcp"][:2]) - np.array(a["tcp"][:2])
        g = np.array(a["goal"][:2]) - np.array(a["tcp"][:2])
        if d is None or np.linalg.norm(mv) < 0.002 or a["err_mm"] < 50: continue
        th = math.degrees(math.atan2(d[0]*mv[1]-d[1]*mv[0], d@mv))
        ang[a["dec"]["dir_xy"]].append(th)
        # angle between commanded dir and true goal dir (quantization)
        goalang.append(abs(math.degrees(math.atan2(d[0]*g[1]-d[1]*g[0], d@g))))
for k, v in sorted(ang.items()):
    v = np.array(v); print(f"{k:18s} n={len(v):4d} median_signed={np.median(v):6.1f} within45={np.mean(abs(v)<45):.2f} abs>135={np.mean(abs(v)>135):.2f}")
print("cmd-vs-goal quantization angle p50/p90", np.percentile(goalang,[50,90]).round(1))
