"""Real-depth D resolver: error decomposition and two improved resolvers (user-log 171 follow-up), RB2 object contact
points (548 H rows: point = contact TCP projected, target = FK TCP at the contact, stereo depth frames).
Decomposition per row: camera part = T4 reprojection (2 / 5 px) turned into metres at the point depth (e * z / f);
error split into along-ray (depth) and lateral components.
Resolvers (all back-project along the ray through the point):
  base   5x5 depth patch median at the point (current dh.converter)
  med    median of the valid depth inside the SAM mask of the named object (mask containing / nearest the point)
  p20    20th percentile (near) of the valid mask depth
  plane  RANSAC plane through the mask's 3-D points, ray-plane intersection
usage (pod, python 3.12 + sam3 / e3st sites, 1 GPU briefly): python -m xemb.rb2_dtest2 DEPTH_DIR T4_NPZ RB2_H OUT_JSON"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np


def ray(K, uv):
    d = np.array([(uv[0] - K[0, 2]) / K[0, 0], (uv[1] - K[1, 2]) / K[1, 1], 1.0])
    return d


THIN = {"wrench", "screwdriver", "brush", "tube", "pliers", "scissors", "handle", "pen", "marker"}
HOLLOW = {"crate", "box", "basket", "bin", "bag", "container", "tray", "cup", "bowl"}


def group_of(name):
    w = set(name.split())
    return "hollow_or_box" if w & HOLLOW else ("thin" if w & THIN else "compact")


def plane_fit(P, it=200, tol=0.005, rng=np.random.default_rng(0)):
    best, bi = None, -1
    for _ in range(it):
        s = P[rng.choice(len(P), 3, replace=False)]
        n = np.cross(s[1] - s[0], s[2] - s[0])
        if np.linalg.norm(n) < 1e-9:
            continue
        n /= np.linalg.norm(n)
        c = (np.abs((P - s[0]) @ n) < tol).sum()
        if c > bi:
            best, bi = (n, s[0]), c
    return best


def main(depth_dir, t4, rec, outp):
    from harvest.perception.seg import Sam31Image
    import cv2
    z4 = np.load(t4)
    E, K = z4["E"].astype(float), z4["K"].astype(float)
    Tbc = np.linalg.inv(E)
    seg = Sam31Image(thr=0.3)
    out = {k: [] for k in ("base", "base_same_rows", "med", "p20", "plane")}
    dd, dn = {}, {}  # D-definition measures: resolver -> group -> xy / dz ; resolver -> name -> dz
    decomp = {"ray": [], "lat": [], "z": [], "no_mask": 0}
    by = {}
    for line in open(rec):
        r = json.loads(line)
        a = json.loads(r["answer"])
        img_p = r["images"][0]
        m = re.search(r"ep(\d+)/f(\d+)\.jpg$", img_p)
        if not m:
            continue
        dp = os.path.join(depth_dir, f"ep{int(m.group(1)):06d}_f{int(m.group(2)):04d}.npz")
        if not os.path.exists(dp):
            continue
        name = re.search(r"Point to the (.+?) in image 1", r["prompt"]).group(1).split(" where")[0].split(" that")[0]
        d = np.load(dp)["depth"].astype(float)
        d[d <= 0] = np.nan
        H, W = d.shape
        uv = np.array([a["point_2d"][0] * W / 1000.0, a["point_2d"][1] * H / 1000.0])
        tgt_c = E[:3, :3] @ np.array(a["position_m"]) + E[:3, 3]  # target in camera frame
        rv = ray(K, uv)

        tgt_b = np.array(a["position_m"], float)
        grp = group_of(name)

        def to_err(zv, key=None):
            if zv is None or not np.isfinite(zv):
                return None
            pc = rv * zv
            if key:  # D definition: horizontal xy error vs the FK TCP, and the height offset (surface - TCP z)
                xb = Tbc[:3, :3] @ pc + Tbc[:3, 3]
                dd.setdefault(key, {}).setdefault(grp, {"xy": [], "dz": []})
                dd[key][grp]["xy"].append(float(np.linalg.norm(xb[:2] - tgt_b[:2])))
                dd[key][grp]["dz"].append(float(xb[2] - tgt_b[2]))
                dn.setdefault(key, {}).setdefault(name, []).append(float(xb[2] - tgt_b[2]))
            return float(np.linalg.norm(pc - tgt_c)), pc

        u, v = int(round(uv[0])), int(round(uv[1]))
        patch = d[max(0, v - 2):v + 3, max(0, u - 2):u + 3]
        zb = float(np.nanmedian(patch)) if np.isfinite(patch).any() else None
        e = to_err(zb, "base")
        e_base = e[0] if e else None
        by.setdefault(name, {k: [] for k in out})
        if e:
            out["base"].append(e[0])
            by[name]["base"].append(e[0])
            dv = e[1] - tgt_c
            rr = tgt_c / np.linalg.norm(tgt_c)
            decomp["ray"].append(float(dv @ rr))
            decomp["lat"].append(float(np.linalg.norm(dv - (dv @ rr) * rr)))
            decomp["z"].append(float(tgt_c[2]))
        img = cv2.imread(img_p)
        res, _ = seg.segment(img[:, :, ::-1], [name])
        ms = [mk.astype(bool) for sc, mk in res[name] if sc >= 0.3]
        if not ms:
            ms = [mk.astype(bool) for sc, mk in seg.segment(img[:, :, ::-1], [name.split()[-1]])[0][name.split()[-1]]
                  if sc >= 0.3]
        if not ms:
            decomp["no_mask"] += 1
            continue
        mk = min(ms, key=lambda q: 0 if q[v, u] else np.min(np.hypot(*(np.array(np.nonzero(q)[::-1]) - uv[:, None]))))
        vals = d[mk & np.isfinite(d)]
        if len(vals) < 20:
            continue
        if e_base is not None:  # the current resolver on exactly the rows the mask resolvers see
            out["base_same_rows"].append(e_base)
            to_err(zb, "base_same_rows")
        for k, zv in (("med", float(np.median(vals))), ("p20", float(np.percentile(vals, 20)))):
            e = to_err(zv, k)
            if e:
                out[k].append(e[0])
                by[name][k].append(e[0])
        ys, xs = np.nonzero(mk & np.isfinite(d))
        zz = d[ys, xs]
        P = np.c_[(xs - K[0, 2]) * zz / K[0, 0], (ys - K[1, 2]) * zz / K[1, 1], zz]
        if len(P) > 2000:
            P = P[np.random.default_rng(1).choice(len(P), 2000, replace=False)]
        pl = plane_fit(P)
        if pl is not None:
            n, p0 = pl
            den = rv @ n
            if abs(den) > 1e-6:
                t = (p0 @ n) / den
                e = to_err(t, "plane")
                if e:
                    out["plane"].append(e[0])
                    by[name]["plane"].append(e[0])

    def st(x):
        x = np.asarray(x)
        return {"n": int(len(x)), "median_cm": round(float(np.median(x)) * 100, 2),
                "le2cm": round(float((x <= 0.02).mean()), 3), "le5cm": round(float((x <= 0.05).mean()), 3)} if len(x) else None
    z = np.array(decomp["z"])
    res = {"resolvers": {k: st(v) for k, v in out.items()},
           "decomposition": {"along_ray_signed_median_cm": round(float(np.median(decomp["ray"])) * 100, 2),
                             "along_ray_abs_median_cm": round(float(np.median(np.abs(decomp["ray"]))) * 100, 2),
                             "lateral_median_cm": round(float(np.median(decomp["lat"])) * 100, 2),
                             "depth_median_m": round(float(np.median(z)), 3),
                             "camera_2px_cm": round(float(np.median(2 * z / K[0, 0])) * 100, 2),
                             "camera_5px_cm": round(float(np.median(5 * z / K[0, 0])) * 100, 2),
                             "no_mask": decomp["no_mask"]},
           "by_name": {k: {kk: st(vv) for kk, vv in v.items()} for k, v in by.items()}}
    def dstat(v):
        xy, dz = np.asarray(v["xy"]), np.asarray(v["dz"])
        return {"n": int(len(xy)), "xy_median_cm": round(float(np.median(xy)) * 100, 2),
                "xy_le2cm": round(float((xy <= 0.02).mean()), 3), "dz_median_cm": round(float(np.median(dz)) * 100, 2),
                "dz_iqr_cm": round(float(np.subtract(*np.percentile(dz, [75, 25]))) * 100, 2),
                "dz_std_cm": round(float(np.std(dz)) * 100, 2)}
    res["d_definition"] = {k: {g: dstat(v) for g, v in gs.items()} for k, gs in dd.items()}
    res["dz_by_name"] = {k: {n: {"n": len(v), "median_cm": round(float(np.median(v)) * 100, 2),
                                 "iqr_cm": round(float(np.subtract(*np.percentile(v, [75, 25]))) * 100, 2)}
                             for n, v in ns.items()} for k, ns in dn.items()}
    json.dump(res, open(outp, "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("resolvers", "d_definition")}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
