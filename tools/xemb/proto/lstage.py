"""L-stage summary (CPU): label accuracy WITHOUT training, on calibrated open sets with the calibration hidden.
  route 2 (Molmo2-ER per-frame pointing) vs GT gripper points (MolmoBot) / gripper masks (BEHAVIOR);
  T5 front-end (CoTracker3 from one query) vs GT gripper points (MolmoBot), grasp / place label pixel error.
usage: lstage.py OUT_JSON"""
import json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
import numpy as np
from xemb import gates as Q

R = "/data/harvest/out/xemb_proto"
gt = json.load(open(f"{R}/point/gt.json"))
res = {}
rows = [json.loads(x) for x in open(f"{R}/point/points.jsonl")]
for src in ("mb", "b1k"):
    ok_named = ok_other = none = n = 0
    errs = []
    for r in rows:
        if not r["key"].startswith(src + "|"):
            continue
        g = gt[r["key"]]
        if src == "mb":
            pts = np.array(g["pts"], float)
            pts[pts < 0] = np.nan
            if not np.isfinite(pts).all(1).any():
                continue  # named gripper not visible
            oth = np.array(g["other"], float)
            oth[oth < 0] = np.nan
            n += 1
            if r["point"] is None:
                none += 1
                continue
            a = Q.near_points(r["point"], pts, k=0.5, min_px=15)
            b = np.isfinite(oth).all(1).any() and Q.near_points(r["point"], oth, k=0.5, min_px=15)
            ok_named += a
            ok_other += (b and not a)
            errs.append(float(np.min(np.linalg.norm(pts[np.isfinite(pts).all(1)] - np.asarray(r["point"]), axis=1))))
        else:
            z = np.load(g["mask"])
            if z["m"].sum() < 30:
                continue
            n += 1
            if r["point"] is None:
                none += 1
                continue
            a = Q.on_mask(r["point"], z["m"], r_px=6)
            b = Q.on_mask(r["point"], z["o"], r_px=6) if z["o"].sum() else False
            ok_named += a
            ok_other += (b and not a)
    res[f"route2_pointing_{src}"] = {"visible_cases": n, "correct_gripper": round(ok_named / max(1, n), 3),
                                     "other_gripper": round(ok_other / max(1, n), 3), "no_point": round(none / max(1, n), 3),
                                     "dist_to_nearest_gt_point_med_px": round(float(np.median(errs)), 1) if errs else None}
t5 = json.load(open(f"{R}/t5/t5_mb.json"))
ge = [x["grip_err_med_px"] for x in t5 if x["grip_err_med_px"] is not None]
le = [x["grip_le20"] for x in t5 if x["grip_le20"] is not None]
gl = [v for x in t5 for v in x["grasp_label_err_px"]]
pl = [v for x in t5 for v in x["place_label_err_px"]]
res["T5_tracker_one_gt_seed_mb"] = {"episodes": len(t5), "grip_err_med_of_eps_px": round(float(np.median(ge)), 1),
                                     "grip_le20px_mean": round(float(np.mean(le)), 3),
                                     "grasp_label_err_med_px": round(float(np.median(gl)), 1) if gl else None,
                                     "grasp_label_le40px": round(float(np.mean(np.array(gl) <= 40)), 3) if gl else None,
                                     "place_label_err_med_px": round(float(np.median(pl)), 1) if pl else None,
                                     "n_grasp": len(gl), "n_place": len(pl)}
json.dump(res, open(sys.argv[1], "w"), indent=1)
print(json.dumps(res, indent=1))
