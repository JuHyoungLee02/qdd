import json, glob, os, collections, math
import numpy as np
R = "/data/harvest/out/couple/cj1/res/ov"
DIRS = {"plus_x": (1, 0), "minus_x": (-1, 0), "plus_y": (0, 1), "minus_y": (0, -1)}
def dvec(s):
    if s in (None, "none"): return None
    v = np.zeros(2)
    for k, (a, b) in DIRS.items():
        if k in s: v += (a, b)
    # handle combined names like plus_x_minus_y
    parts = s.split("_")
    v = np.zeros(2)
    for i in range(0, len(parts) - 1, 2):
        sg = 1 if parts[i] == "plus" else -1
        ax = parts[i + 1]
        v[0 if ax == "x" else 1] += sg
    n = np.linalg.norm(v)
    return v / n if n else None

stats = collections.defaultdict(list)
jump = []
prog = collections.defaultdict(list)
ends = collections.Counter()
grip = collections.Counter()
lat = []
for f in sorted(glob.glob(R + "/*/s*/vla_steps.jsonl")):
    rows = [json.loads(l) for l in open(f)]
    cj = json.load(open(os.path.join(os.path.dirname(f), "cj.json")))
    ends[(cj["fail_stage"], cj["end_reason"])] += 1
    for a, b in zip(rows, rows[1:]):
        if a.get("chunk") is None or b.get("tcp") is None: continue
        lat.append(a["lat_s"])
        c0 = np.array(a["chunk"][0][:7]); q = np.array(a["joint_pos"][:7])
        jump.append(np.abs(c0 - q).max())
        mv = np.array(b["tcp"]) - np.array(a["tcp"])
        d = dvec(a["dec"]["dir_xy"])
        key = (a["phase"], a["dec"]["mag_coarse"])
        dist_bin = "far>5cm" if a["err_mm"] > 50 else ("mid2-5" if a["err_mm"] > 20 else "near<2")
        if d is not None and np.linalg.norm(mv[:2]) > 0.002:
            ok = float(np.dot(mv[:2] / np.linalg.norm(mv[:2]), d) > math.cos(math.radians(45)))
            stats[dist_bin].append(ok); stats["ph:" + a["phase"]].append(ok)
        elif d is not None:
            stats["stall_" + dist_bin].append(1)
        prog[dist_bin].append(a["err_mm"] - b["err_mm"])
        # z compliance
        dz = a["dec"]["dir_z"]
        if dz in ("up", "down") and abs(mv[2]) > 0.002:
            stats["z_" + dist_bin].append(float((mv[2] > 0) == (dz == "up")))
        g0 = a["chunk"][0][7]; gl = a["chunk"][-1][7]
        grip[(a["phase"], "grip_close_pred" if gl < g0 - 0.01 else ("grip_open_pred" if gl > g0 + 0.01 else "hold"))] += 1
print("episodes end:", dict(ends))
for k, v in sorted(stats.items()):
    print(f"{k:22s} n={len(v):5d} mean={np.mean(v):.3f}")
for k, v in prog.items():
    v = np.array(v); print(f"progress {k:8s} n={len(v)} mean_mm={v.mean():.1f} frac_worse={np.mean(v<0):.2f}")
j = np.array(jump); print("chunk0-vs-q max-abs rad p50/p90/p99", np.percentile(j, [50, 90, 99]).round(3), "frac>0.04", (j > 0.04).mean().round(3))
print("lat p50/p95", np.percentile(lat, [50, 95]).round(3))
for k, v in sorted(grip.items()): print("grip", k, v)
