"""Real-depth D resolver test (user-log 171): RB2 stereo metric depth (Fast-FoundationStereo, frames that passed the 2 cm
arm-mesh gate) + T4 head camera. D resolver = point + measured depth -> xyz (dh.converter: median of a 5x5 depth patch
at the point, back-projected, camera -> base). Two point sets, both scored in 3-D against FK:
  A  gripper points: the FK end effector of both arms projected into every depth frame (the D 'where is the gripper')
  B  object points : the RB2 grasp / place H rows (point = the contact TCP projected, target = position_m = FK TCP)
Reported: depth-missing rate at the point, 3-D error (median / p90), share within 2 / 5 cm, error along the viewing ray
vs lateral, per object name (B).
usage (pod): python -m xemb.rb2_dtest DEPTH_DIR T4_NPZ MARR_EPS_DIR RB2_H_RECORDS OUT_JSON"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

from . import dh as DH


def stats(e):
    e = np.asarray(e, float)
    if not len(e):
        return None
    return {"n": int(len(e)), "median_cm": round(float(np.median(e)) * 100, 2),
            "p90_cm": round(float(np.percentile(e, 90)) * 100, 2), "le2cm": round(float((e <= 0.02).mean()), 3),
            "le5cm": round(float((e <= 0.05).mean()), 3)}


def main(depth_dir, t4, eps_dir, rec_d, outp):
    z = np.load(t4)
    E, K = z["E"].astype(float), z["K"].astype(float)
    Tbc = np.linalg.inv(E)
    res = {}
    # A: gripper points
    errA, rayA, missA, nA = [], [], 0, 0
    cache = {}
    for p in sorted(glob.glob(os.path.join(depth_dir, "ep*_f*.npz"))):
        m = re.search(r"ep(\d+)_f(\d+)", p)
        ep, k = int(m.group(1)), int(m.group(2))
        if ep not in cache:
            q = os.path.join(eps_dir, f"RB2_ep{ep:06d}.npz")
            cache = {ep: np.load(q) if os.path.exists(q) else None}
        ee = cache[ep]
        if ee is None or k >= len(ee["ee_l"]):
            continue
        d = np.load(p)["depth"].astype(float)
        d[d <= 0] = np.nan
        H, W = d.shape
        for key in ("ee_l", "ee_r"):
            x = ee[key][k]
            pc = E[:3, :3] @ x + E[:3, 3]
            if pc[2] <= 0.1:
                continue
            uv = K @ pc / pc[2]
            if not (0 <= uv[0] < W and 0 <= uv[1] < H):
                continue
            nA += 1
            xb = DH.converter(K, Tbc, d, uv[:2])
            if xb is None:
                missA += 1
                continue
            errA.append(float(np.linalg.norm(xb - x)))
            ray = pc / np.linalg.norm(pc)
            rayA.append(float((E[:3, :3] @ xb + E[:3, 3] - pc) @ ray))
    res["A_gripper"] = {"points": nA, "depth_missing": round(missA / max(1, nA), 3), "err": stats(errA),
                        "ray_signed_median_cm": round(float(np.median(rayA)) * 100, 2) if rayA else None}
    # B: object points from the RB2 D rows (grasp / place)
    by, missB, nB, errB = {}, 0, 0, []
    for line in open(rec_d):
        r = json.loads(line)
        a = json.loads(r["answer"])
        img = r["images"][0]
        m = re.search(r"ep(\d+)/f(\d+)\.jpg$", img)
        if not m:
            continue
        dp = os.path.join(depth_dir, f"ep{int(m.group(1)):06d}_f{int(m.group(2)):04d}.npz")
        if not os.path.exists(dp):
            continue
        hr = re.search(r"Point to the (.+?) in image 1", r["prompt"])
        name = hr.group(1).split(" where")[0].split(" that")[0] if hr else "?"
        d = np.load(dp)["depth"].astype(float)
        d[d <= 0] = np.nan
        H, W = d.shape
        uv = [a["point_2d"][0] * W / 1000.0, a["point_2d"][1] * H / 1000.0]
        nB += 1
        xb = DH.converter(K, Tbc, d, uv)
        by.setdefault(name, {"n": 0, "miss": 0, "err": []})["n"] += 1
        if xb is None:
            missB += 1
            by[name]["miss"] += 1
            continue
        t = a.get("position_m")  # H rows carry the FK TCP target at the contact (base frame)
        if t is not None:
            e = float(np.linalg.norm(xb - np.asarray(t)))
            errB.append(e)
            by[name]["err"].append(e)
    res["B_object"] = {"points": nB, "depth_missing": round(missB / max(1, nB), 3), "err": stats(errB),
                       "by_name": {k: {"n": v["n"], "missing": round(v["miss"] / max(1, v["n"]), 3), "err": stats(v["err"])}
                                   for k, v in sorted(by.items(), key=lambda kv: -kv[1]["n"])}}
    json.dump(res, open(outp, "w"), indent=1)
    print(json.dumps(res, indent=1)[:3000])


if __name__ == "__main__":
    main(*sys.argv[1:6])
