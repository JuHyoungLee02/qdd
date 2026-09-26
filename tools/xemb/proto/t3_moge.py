"""T3 (GPU): MoGe-2 monocular metric geometry on BEHAVIOR frames with GT depth (L-stage: depth, focal, object-centre and
plane errors) and on ROBOTIS RB2 frames (focal estimate vs ZED spec / T1). usage: t3_moge.py B1K_DIR RB2_ROOT OUT"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/tmp/MoGe")
sys.path.insert(0, "/data/harvest/pylib_moge")
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
import cv2
import numpy as np
import torch
from moge.model.v2 import MoGeModel
from xemb import geom as G

b1k, rb2, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
model = MoGeModel.from_pretrained("Ruicheng/moge-2-vitl-normal").cuda().eval()
K_GT = np.array([[306.0, 0, 360], [0, 306.0, 360], [0, 0, 1]])


def infer(img_bgr):
    t = torch.from_numpy(img_bgr[:, :, ::-1].copy()).float().div(255).permute(2, 0, 1).cuda()
    with torch.inference_mode():
        o = model.infer(t)
    return {k: v.detach().cpu().numpy() for k, v in o.items() if torch.is_tensor(v)}


def plane(pts):
    n, d, inl = G.fit_plane(pts[:: max(1, len(pts) // 4000)], tol=0.01)
    return n, d, inl


res = {"frames": [], "rb2": []}
idx = json.load(open(os.path.join(b1k, "index.json")))
for it in idx:
    img = cv2.imread(os.path.join(b1k, it["key"] + ".jpg"))
    z = np.load(os.path.join(b1k, it["key"] + ".npz"))
    D = z["depth"]
    o = infer(img)
    Dp, P, m = o["depth"], o["points"], o["mask"].astype(bool)
    H, W = D.shape
    fx_p = float(o["intrinsics"][0, 0] * W)
    v = m & (D > 0.1) & (D < 4.0) & np.isfinite(Dp)
    ae = np.abs(Dp[v] - D[v])
    rel = ae / D[v]
    fr = {"key": it["key"], "fx_pred": fx_p, "absrel": float(np.median(rel)), "abs_cm_med": float(np.median(ae) * 100),
          "delta1": float(np.mean(np.maximum(Dp[v] / D[v], D[v] / Dp[v]) < 1.25)), "scale": float(np.median(Dp[v] / D[v])),
          "objs": [], "planes": []}
    for oi, ob in enumerate(it["objs"]):
        mk = cv2.erode(z["objm"][oi].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        if mk.sum() < 50:
            continue
        gt = np.asarray(ob["gt_c"])
        Pg = G.backproject(K_GT, D, mk, dmin=0.05, dmax=9.9)  # GT depth, visible surface (the 9.1 cm reference)
        Pp = P[mk & m]
        Pp = Pp[np.isfinite(Pp).all(1)]
        if len(Pg) < 30 or len(Pp) < 30:
            continue
        mg, mp = np.median(Pg, 0), np.median(Pp, 0)
        ray = gt / np.linalg.norm(gt)
        fr["objs"].append({"name": ob["name"], "err_gtdepth_cm": float(np.linalg.norm(mg - gt) * 100),
                           "err_pseudo_cm": float(np.linalg.norm(mp - gt) * 100),
                           "pseudo_vs_gtdepth_surface_cm": float(np.linalg.norm(mp - mg) * 100),
                           "pseudo_along_ray_cm": float((mp - gt) @ ray * 100),
                           "pseudo_lateral_cm": float(np.linalg.norm((mp - gt) - ((mp - gt) @ ray) * ray) * 100)})
    for si in range(len(z["surfm"])):
        mk = z["surfm"][si] & m
        Pg = G.backproject(K_GT, D, z["surfm"][si], dmin=0.05, dmax=9.9)
        Pp = P[mk]
        Pp = Pp[np.isfinite(Pp).all(1)]
        if len(Pg) < 200 or len(Pp) < 200:
            continue
        ng, dg, ig = plane(Pg)
        npp, dp, ip = plane(Pp)
        if ig < 0.5 or ip < 0.5:
            continue
        fr["planes"].append({"cam_to_plane_gt_cm": float(abs(dg) * 100), "cam_to_plane_pseudo_cm": float(abs(dp) * 100),
                             "err_cm": float(abs(abs(dp) - abs(dg)) * 100),
                             "normal_deg": float(np.degrees(np.arccos(min(1, abs(ng @ npp)))))})
    res["frames"].append(fr)
    print(json.dumps({"key": it["key"], "fx": round(fx_p, 1), "absrel": round(fr["absrel"], 3),
                      "objs": [round(x["err_pseudo_cm"], 1) for x in fr["objs"]],
                      "planes": [round(x["err_cm"], 1) for x in fr["planes"]]}), flush=True)
# RB2 (open, uncalibrated): focal estimates
rng = np.random.default_rng(0)
imgs = sorted(glob.glob(os.path.join(rb2, "frames", "RB2", "ep*", "f0010.jpg")))
for p in [imgs[i] for i in rng.permutation(len(imgs))[:120]]:
    img = cv2.imread(p)
    o = infer(img)
    res["rb2"].append({"img": p, "fx_pred": float(o["intrinsics"][0, 0] * img.shape[1]),
                       "fy_pred": float(o["intrinsics"][1, 1] * img.shape[0])})
json.dump(res, open(os.path.join(out, "t3_moge.json"), "w"))
fr = res["frames"]
ob = [x for f in fr for x in f["objs"]]
pl = [x for f in fr for x in f["planes"]]
summ = {"frames": len(fr), "fx_pred_med": float(np.median([f["fx_pred"] for f in fr])), "fx_gt": 306.0,
        "absrel_med": float(np.median([f["absrel"] for f in fr])), "abs_cm_med": float(np.median([f["abs_cm_med"] for f in fr])),
        "delta1_med": float(np.median([f["delta1"] for f in fr])), "scale_med": float(np.median([f["scale"] for f in fr])),
        "obj_n": len(ob), "obj_err_gtdepth_cm_med": float(np.median([x["err_gtdepth_cm"] for x in ob])) if ob else None,
        "obj_err_pseudo_cm_med": float(np.median([x["err_pseudo_cm"] for x in ob])) if ob else None,
        "obj_pseudo_vs_surface_cm_med": float(np.median([x["pseudo_vs_gtdepth_surface_cm"] for x in ob])) if ob else None,
        "obj_pseudo_lateral_cm_med": float(np.median([x["pseudo_lateral_cm"] for x in ob])) if ob else None,
        "plane_n": len(pl), "plane_err_cm_med": float(np.median([x["err_cm"] for x in pl])) if pl else None,
        "plane_err_cm_p90": float(np.percentile([x["err_cm"] for x in pl], 90)) if pl else None,
        "plane_normal_deg_med": float(np.median([x["normal_deg"] for x in pl])) if pl else None,
        "rb2_fx_pred_med": float(np.median([r["fx_pred"] for r in res["rb2"]])),
        "rb2_fx_pred_p10_p90": [float(np.percentile([r["fx_pred"] for r in res["rb2"]], q)) for q in (10, 90)]}
json.dump(summ, open(os.path.join(out, "t3_summary.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
