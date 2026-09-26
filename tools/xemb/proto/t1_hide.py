"""T1 hide-and-recover on a CALIBRATED open set (MolmoBot RBY1, 50 train packages): hide the camera calibration,
recover it from FK 3-D gripper (commanded ee_pose, lag 1) + 2-D detections, compare with the hidden GT.
Detectors: gt (mean of the 10 GT gripper points; the ceiling), point (Molmo2-ER per-frame pointing, every 10th frame),
track_oracle / track_point (shared front-end fused tracks seeded by one GT point / by up to 3 pointings).
usage: t1_hide.py CACHE_DIR OUT_JSON"""
import json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/data/upper_vlm_survey/pylib")
import numpy as np
from xemb import geom as G
from xemb import selfcal as C
from xemb import src_molmobot as MB
from xemb import track as TK

cache, outp = sys.argv[1], sys.argv[2]
pts = {}
for line in open("/data/harvest/out/xemb_proto/point/points.jsonl"):
    r = json.loads(line)
    if r["key"].startswith("mb|"):
        _, name, k, arm = r["key"].split("|")
        pts[(name, int(k), arm)] = r["point"]
eps = []
Tgt = []
for e in MB.episodes("/data/harvest/out/xemb_proto/src/mb_rby1"):
    cp = os.path.join(cache, f"{e.name}.npz")
    if not os.path.exists(cp):
        continue
    c = TK.load(cp)
    n = min(e.n, c["meta"]["n"])
    rec = {"name": e.name, "n": n, "p": {}, "R": {}, "u": {}}
    for arm in ("left", "right"):
        P = np.array([e.T_base_ee(max(k - 1, 0))[:3, 3] for k in range(n)])
        Rr = np.array([e.T_base_ee(max(k - 1, 0))[:3, :3] for k in range(n)])
        rec["p"][arm], rec["R"][arm] = P, Rr
        gt = np.array([np.nanmean(e.pts(f"{arm}_gripper", "head_camera", k), 0) for k in range(n)])
        det = np.full((n, 2), np.nan)
        for k in range(n):
            q = pts.get((e.name, k, arm))
            if q is not None:
                det[k] = q
        rec["u"][("gt", arm)] = gt
        rec["u"][("point", arm)] = det
        for s in ("oracle", "point"):
            rec["u"][(f"track_{s}", arm)] = c["fused"].get(f"grip_{arm}_{s}", np.full((n, 2), np.nan))[:n]
    K = e.K("head_camera", 0)
    Ts = [G.inv_T(e.T_world_base(k)) @ G.inv_T(e.E("head_camera", k)) for k in range(0, n, 10)]  # T_base_cam GT
    rec["Tbc_gt"] = Ts
    rec["K"] = K
    eps.append(rec)
    Tgt += Ts
# spread of the GT camera in the base frame (is pooling across episodes legitimate?)
ref = Tgt[0]
spread = np.array([C.pose_error(G.inv_T(T), G.inv_T(ref)) for T in Tgt])
res = {"episodes": len(eps), "gt_cam_spread_rot_deg_p90": round(float(np.percentile(spread[:, 0], 90)), 2),
       "gt_cam_spread_centre_cm_p90": round(float(np.percentile(spread[:, 1], 90) * 100), 2)}
K = eps[0]["K"]
sanity = []
for det in ("gt", "point", "track_oracle", "track_point"):
    per = []
    for ep in eps:  # per episode (head pose may differ between episodes)
        E_gt = G.inv_T(ep["Tbc_gt"][0])
        if det == "gt":  # sanity: the hidden GT camera itself, zero offset
            g0 = np.r_[C.project_many(K, E_gt, ep["p"]["left"]), C.project_many(K, E_gt, ep["p"]["right"])]
            gu = np.r_[ep["u"][("gt", "left")], ep["u"][("gt", "right")]]
            sanity.append(float(np.nanmedian(np.linalg.norm(g0 - gu, axis=1))))
        pL, pR = ep["p"]["left"], ep["p"]["right"]
        uL, uR = ep["u"][(det, "left")], ep["u"][(det, "right")]
        f = C.selfcal_offset(pL, ep["R"]["left"], pR, ep["R"]["right"], uL, uR, K, fit_fx=False)
        if f is None:
            per.append(None)
            continue
        rot, dist = C.pose_error(f["E"], E_gt)
        # reprojection of the GT gripper points with the recovered camera vs with the GT camera (held-in frames)
        g = np.r_[ep["u"][("gt", "left")], ep["u"][("gt", "right")]]
        pr = np.r_[C.project_offset(f, pL, ep["R"]["left"], "left"), C.project_offset(f, pR, ep["R"]["right"], "right")]
        d = np.linalg.norm(pr - g, axis=1)
        per.append({"rot_deg": rot, "centre_cm": dist * 100, "n": f["n"], "reproj_vs_gt_med_px": float(np.nanmedian(d))})
    ok = [x for x in per if x]
    res[det] = {"eps_solved": len(ok), "eps": len(per),
                "rot_deg_med": round(float(np.median([x["rot_deg"] for x in ok])), 2) if ok else None,
                "centre_cm_med": round(float(np.median([x["centre_cm"] for x in ok])), 2) if ok else None,
                "centre_cm_p90": round(float(np.percentile([x["centre_cm"] for x in ok], 90)), 2) if ok else None,
                "reproj_vs_gt_med_px": round(float(np.median([x["reproj_vs_gt_med_px"] for x in ok])), 2) if ok else None,
                "le_2cm_rate": round(float(np.mean([x["centre_cm"] <= 2 for x in ok])), 3) if ok else None}
res["gt_camera_zero_offset_resid_med_px"] = round(float(np.nanmedian(sanity)), 2) if sanity else None
json.dump(res, open(outp, "w"), indent=1)
print(json.dumps(res, indent=1))
