"""Head depth distribution of L8-D / L8-X calls (for the depth encoding range of tracks H / D). usage:
  python depth_stats.py <collect root> [max calls per bucket]
Per bucket (<split>/<vdir>) and overall: percentiles 1 / 5 / 50 / 95 / 99 of the finite head z-depth (m):
  all      every pixel;
  lower60  image rows >= 40 % (table, objects, floor beyond);
  objects  pixels whose back-projected point (cams.json head camera, robot frame) lies 0.5-20 cm above the
           episode's table top (scene.json table_z; furniture: the chosen surface) and inside x 0.2-0.8, y -0.6-0.3:
           the objects on the working surface (the arm above 20 cm is excluded)."""
import glob
import json
import os
import sys

import numpy as np

root = sys.argv[1]
cap = int(sys.argv[2]) if len(sys.argv) > 2 else 20
P = (1, 5, 50, 95, 99)


def points(cam, z):
    H, W = z.shape
    u, v = np.meshgrid(np.arange(W), np.arange(H))
    x = (u - cam["cx"]) / cam["fx"] * z
    y = (v - cam["cy"]) / cam["fy"] * z
    pc = np.stack([x, y, z], -1)
    return pc @ np.asarray(cam["R"], float).T + np.asarray(cam["t"], float)


out, acc = {}, {"all": [], "lower60": [], "objects": []}
for b in sorted(glob.glob(os.path.join(root, "*", "*"))):
    files = sorted(glob.glob(os.path.join(b, "*", "calls", "c*", "head_depth.npz")))[:cap]
    if not files:
        continue
    per = {"all": [], "lower60": [], "objects": []}
    for f in files:
        z = np.load(f)["depth"].astype(float)
        ok = np.isfinite(z) & (z > 0)
        h = z.shape[0]
        per["all"].append(z[ok][::7])
        lo = np.zeros_like(ok)
        lo[int(0.4 * h):] = True
        per["lower60"].append(z[ok & lo][::7])
        ep = f.split(os.sep + "calls" + os.sep)[0]
        sc = json.load(open(os.path.join(ep, "scene.json")))
        cam = json.load(open(os.path.join(os.path.dirname(f), "cams.json")))["head"]
        pw = points(cam, np.where(ok, z, np.nan))
        hz = pw[..., 2] - float(sc["table_z"])
        m = ok & (hz > 0.005) & (hz < 0.20) & (pw[..., 0] > 0.2) & (pw[..., 0] < 0.8) & (pw[..., 1] > -0.6) & \
            (pw[..., 1] < 0.3)
        per["objects"].append(z[m])
    row = {"calls": len(files)}
    for k in per:
        v = np.concatenate(per[k]) if per[k] else np.zeros(0)
        acc[k].append(v)
        row[k] = [round(float(x), 3) for x in np.percentile(v, P)] if v.size else None
    out[os.path.relpath(b, root)] = row
out["OVERALL"] = {"percentiles": P, **{k: [round(float(x), 3) for x in np.percentile(np.concatenate(v), P)]
                                       for k, v in acc.items() if v}}
print(json.dumps(out, indent=1))
