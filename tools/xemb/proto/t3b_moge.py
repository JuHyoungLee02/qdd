"""T3 re-check (GPU): MoGe-2 on BEHAVIOR frames; errors raw vs per-frame scale aligned to ONE known 3-D point = the FK
end-effector (visible gripper, depth at its pixel), vs scale+shift aligned by least squares to both grippers' depths.
Also the oracle upper bound: scale aligned to the GT table plane distance (not usable at run time; shows the ceiling).
usage: t3b_moge.py DIR OUT_JSON"""
import json, os, sys
sys.path.insert(0, "/data/harvest/tmp/MoGe")
sys.path.insert(0, "/data/harvest/pylib_moge")
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
import cv2
import numpy as np
import torch
from moge.model.v2 import MoGeModel
from xemb import geom as G

d, outp = sys.argv[1], sys.argv[2]
model = MoGeModel.from_pretrained("Ruicheng/moge-2-vitl-normal").cuda().eval()
K = np.array([[306.0, 0, 360], [0, 306.0, 360], [0, 0, 1]])
idx = json.load(open(os.path.join(d, "index.json")))
rows = []
for it in idx:
    img = cv2.imread(os.path.join(d, it["key"] + ".jpg"))
    z = np.load(os.path.join(d, it["key"] + ".npz"))
    D = z["depth"]
    t = torch.from_numpy(img[:, :, ::-1].copy()).float().div(255).permute(2, 0, 1).cuda()
    with torch.inference_mode():
        o = model.infer(t)
    P = o["points"].cpu().numpy()
    Dp = o["depth"].cpu().numpy()
    mv = o["mask"].cpu().numpy().astype(bool)
    anchors = []
    for a, gk in (("left", "gml"), ("right", "gmr")):
        ee = np.asarray(it["ee_cam"][a])
        uv, zz = G.project(K, np.eye(4), ee)
        gm = z[gk]
        if zz <= 0 or not (0 <= uv[0] < 720 and 0 <= uv[1] < 720) or gm.sum() < 50:
            continue
        # pseudo depth on the gripper mask near the projected EE point (within 25 px)
        ys, xs = np.nonzero(gm)
        near = np.hypot(xs - uv[0], ys - uv[1]) < 25
        if near.sum() < 10:
            continue
        pd = float(np.median(Dp[ys[near], xs[near]]))
        gd = float(np.median(D[ys[near], xs[near]]))  # GT depth at the same pixels (what the anchor should read)
        anchors.append((pd, zz, gd))
    if not anchors:
        continue
    s1 = anchors[0][1] / anchors[0][0]  # one FK point
    if len(anchors) == 2:  # scale + shift from both grippers
        A = np.array([[a[0], 1.0] for a in anchors])
        b = np.array([a[1] for a in anchors])
        s2, sh2 = np.linalg.lstsq(A, b, rcond=None)[0]
    else:
        s2, sh2 = s1, 0.0
    rec = {"key": it["key"], "n_anchor": len(anchors), "fk_vs_gtdepth_at_anchor_cm": float(abs(anchors[0][1] - anchors[0][2]) * 100),
           "objs": [], "planes": []}
    for oi, ob in enumerate(it["objs"]):
        mk = cv2.erode(z["objm"][oi].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & mv
        if mk.sum() < 50:
            continue
        gt = np.asarray(ob["gt_c"])
        Pg = G.backproject(K, D, mk, dmin=0.05, dmax=9.9)
        pr = P[mk]
        pr = pr[np.isfinite(pr).all(1)]
        if len(Pg) < 30 or len(pr) < 30:
            continue
        mg = np.median(Pg, 0)
        e = {}
        for name, s, sh in (("raw", 1.0, 0.0), ("fk1_scale", s1, 0.0), ("fk2_scale_shift", s2, sh2)):
            Pa = pr * s  # scale the point map (shift applied along the ray)
            if sh:
                Pa = Pa + sh * pr / np.linalg.norm(pr, axis=1, keepdims=True)
            m_ = np.median(Pa, 0)
            e[name] = {"vs_gt_centre_cm": float(np.linalg.norm(m_ - gt) * 100),
                       "vs_gt_surface_cm": float(np.linalg.norm(m_ - mg) * 100)}
        e["gtdepth_surface_vs_centre_cm"] = float(np.linalg.norm(mg - gt) * 100)
        rec["objs"].append(e)
    for si in range(len(z["surfm"])):
        mk = z["surfm"][si] & mv
        Pg = G.backproject(K, D, z["surfm"][si], dmin=0.05, dmax=9.9)
        pr = P[mk]
        pr = pr[np.isfinite(pr).all(1)]
        if len(Pg) < 200 or len(pr) < 200:
            continue
        ng, dg, ig = G.fit_plane(Pg[:: max(1, len(Pg) // 4000)], tol=0.01)
        if ig < 0.5:
            continue
        e = {}
        for name, s, sh in (("raw", 1.0, 0.0), ("fk1_scale", s1, 0.0), ("fk2_scale_shift", s2, sh2)):
            Pa = pr * s
            if sh:
                Pa = Pa + sh * pr / np.linalg.norm(pr, axis=1, keepdims=True)
            npp, dp, ip = G.fit_plane(Pa[:: max(1, len(Pa) // 4000)], tol=0.01)
            e[name] = {"plane_dist_err_cm": float(abs(abs(dp) - abs(dg)) * 100),
                       "normal_deg": float(np.degrees(np.arccos(min(1, abs(ng @ npp)))))}
        rec["planes"].append(e)
    rows.append(rec)
    print(it["key"], len(anchors), flush=True)
summ = {"frames": len(rows), "frames_with_2_anchors": sum(r["n_anchor"] == 2 for r in rows),
        "fk_vs_gtdepth_at_anchor_cm_med": float(np.median([r["fk_vs_gtdepth_at_anchor_cm"] for r in rows]))}
for name in ("raw", "fk1_scale", "fk2_scale_shift"):
    oc = [o[name]["vs_gt_centre_cm"] for r in rows for o in r["objs"]]
    os_ = [o[name]["vs_gt_surface_cm"] for r in rows for o in r["objs"]]
    pl = [p[name]["plane_dist_err_cm"] for r in rows for p in r["planes"]]
    summ[name] = {"obj_n": len(oc), "obj_centre_err_cm_med": round(float(np.median(oc)), 2),
                  "obj_centre_le3cm": round(float(np.mean(np.array(oc) <= 3)), 3),
                  "obj_vs_gt_visible_surface_cm_med": round(float(np.median(os_)), 2),
                  "plane_n": len(pl), "plane_err_cm_med": round(float(np.median(pl)), 2) if pl else None,
                  "plane_le3cm": round(float(np.mean(np.array(pl) <= 3)), 3) if pl else None}
summ["gtdepth_surface_vs_centre_cm_med"] = round(float(np.median([o["gtdepth_surface_vs_centre_cm"] for r in rows for o in r["objs"]])), 2)
json.dump({"summary": summ, "rows": rows}, open(outp, "w"))
print(json.dumps(summ, indent=1))
