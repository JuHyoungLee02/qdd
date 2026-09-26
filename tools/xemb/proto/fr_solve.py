"""Franka hide-and-recover (T1) with four 2-D sources: click (GT TCP projection + N(0, 3 px), the FK-click stand-in),
point (Molmo2-ER per frame), track (shared front-end: CoTracker3 seeded by 3 filtered pointings), track_click (seeded
by one click). Camera fixed per episode; solve base -> cam (intrinsics known, and a focal scan variant); compare with
the hidden GT. usage: fr_solve.py DIR   (venv_train, GPU for the tracker)"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/pylib_moge")
import cv2
import numpy as np
import torch
from xemb import selfcal as C
from xemb import track as TK

d = sys.argv[1]
model = torch.hub.load("facebookresearch/co-tracker", "cotracker3_offline").cuda().eval()
pts = {}
for line in open(os.path.join(d, "points.jsonl")):
    r = json.loads(line)
    _, name, k, _ = r["key"].split("|")
    pts[(name, int(k))] = r["point"]
rng = np.random.default_rng(0)
res = {s: [] for s in ("click", "point", "track", "track_click", "click_fx", "track_fx")}
for f in sorted(glob.glob(os.path.join(d, "*.npz"))):
    name = os.path.basename(f)[:-4]
    z = np.load(f)
    idx, K, E, W, H = z["idx"], z["K"], z["E"], int(z["W"]), int(z["H"])
    p, R, uvg = z["tcp"][idx], z["R"][idx], z["uv_gt"][idx]
    inimg = (uvg[:, 0] >= 0) & (uvg[:, 0] < W) & (uvg[:, 1] >= 0) & (uvg[:, 1] < H)
    click = uvg + rng.normal(0, 3.0, uvg.shape)
    click[~inimg] = np.nan
    det = np.array([pts.get((name, int(k))) or [np.nan, np.nan] for k in idx], float)
    frames = np.array([cv2.imread(os.path.join(d, "img", name, f"f{k:04d}.jpg"))[:, :, ::-1] for k in idx])
    v = torch.from_numpy(np.ascontiguousarray(frames)).permute(0, 3, 1, 2)[None].float().cuda()

    def run(qs):
        q = torch.tensor([[float(t), float(x), float(y)] for t, x, y in qs])[None].cuda()
        with torch.inference_mode():
            tr, vis = model(v, queries=q, backward_tracking=True)
        return TK.fuse(tr[0].cpu().numpy(), vis[0].cpu().numpy() > 0.5)[0]

    s = TK.seeds(det, n=3, win=1, max_px=60)
    trk = run([(t, *det[t]) for t in s]) if s else np.full((len(idx), 2), np.nan)
    c0 = next((t for t in range(len(idx)) if np.isfinite(click[t]).all()), None)
    trc = run([(c0, *click[c0])]) if c0 is not None else np.full((len(idx), 2), np.nan)
    nanR = np.full((len(idx), 2), np.nan)
    for src, u, fx in (("click", click, False), ("point", det, False), ("track", trk, False),
                       ("track_click", trc, False), ("click_fx", click, True), ("track_fx", trk, True)):
        K0 = K.copy()
        if fx:
            K0[0, 0] = K0[1, 1] = K[0, 0] * 0.85  # start 15 % off; the solve must find the focal
        fit = C.selfcal_offset(p, R, p, R, u, nanR, K0, fit_fx=fx)
        if fit is None:
            res[src].append(None)
            continue
        rot, dist = C.pose_error(fit["E"], E)
        pr = C.project_offset(fit, p, R, "left")
        e_true = np.linalg.norm(pr - uvg, axis=1)[inimg]
        res[src].append({"ep": name, "rot_deg": rot, "centre_cm": dist * 100, "fx_err_pct": 100 * (fit["K"][0, 0] / K[0, 0] - 1),
                         "reproj_true_tcp_med_px": float(np.nanmedian(e_true)), "offset_m": fit["o_left"].round(3).tolist(),
                         "inlier_frac": fit["inlier_frac"]})
    print(name, {k: (None if not v[-1] else round(v[-1]["centre_cm"], 1)) for k, v in res.items()}, flush=True)
summ = {}
for src, v in res.items():
    ok = [x for x in v if x]
    summ[src] = {"eps": len(v), "solved": len(ok),
                 "centre_cm_med": round(float(np.median([x["centre_cm"] for x in ok])), 2) if ok else None,
                 "rot_deg_med": round(float(np.median([x["rot_deg"] for x in ok])), 2) if ok else None,
                 "reproj_true_tcp_med_px": round(float(np.median([x["reproj_true_tcp_med_px"] for x in ok])), 2) if ok else None,
                 "le_5px_eps": round(float(np.mean([x["reproj_true_tcp_med_px"] <= 5 for x in ok])), 3) if ok else None,
                 "fx_err_pct_med": round(float(np.median([abs(x["fx_err_pct"]) for x in ok])), 2) if ok else None}
json.dump({"summary": summ, "per_episode": res}, open(os.path.join(d, "fr_solve.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
