"""T4b (CPU): gripper-silhouette BOUNDARY alignment (two-sided chamfer between the projected gripper mesh silhouette
and the SAM 3.1 'robot gripper' mask, restricted to 60 px around the projection so background robots do not pull).
Held-out metric (the T1/T4 gate): median symmetric boundary chamfer in full-resolution px + IoU, per frame.
Synthetic check: masks rasterised from a known camera, recover from a perturbed start.
usage: t4b_align.py MASK_DIR OUT_JSON START_NPZ [START_NPZ ...]"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.append("/data/harvest/pylib_moge")
import cv2
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.optimize import minimize
from xemb import selfcal as C
from xemb import urdf_fk as U

MASKS, OUTP, STARTS = sys.argv[1], sys.argv[2], sys.argv[3:]
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
MESH_ROOT = "/data/harvest/tmp/ai_worker"
RAW = "/data/harvest/data/se2e/raw/Task_0002_OrderPicking_lerobot"
W, H = 672, 376
K0 = np.array([[367.0, 0, 336.0], [0, 367.0, 188.0], [0, 0, 1]])
GRIP = [f"gripper_{s}_rh_p12_rn_{p}" for s in "lr" for p in ("base", "r1", "r2", "l1", "l2")] + \
    [f"arm_{s}_link{i}" for s in "lr" for i in (4, 5, 6, 7)]  # SAM gives no separate gripper mask (score 0): the
# silhouette is arm links 4-7 + grippers against the "robot arm" mask boundary near the projection
TR, NEAR = 30.0, 60
m = U.Urdf(URDF)
pts = {}
for v in m.visuals():
    if v["link"] in GRIP:
        mesh = trimesh.load(v["file"].replace("package://", MESH_ROOT + "/"), force="mesh")
        p = mesh.sample(1500 if "gripper" in v["link"] else 1000, seed=0) * np.asarray(v["scale"])
        pts[v["link"]] = np.c_[p, np.ones(len(p))] @ v["T"].T
info = json.load(open(os.path.join(RAW, "meta", "info.json")))
names = info["features"]["observation.state"]["names"]
cache, frames = {}, []
for it in json.load(open(os.path.join(MASKS, "index.json"))):
    ep, k = it["ep"], it["k"]
    if ep not in cache:
        c = ep // info["chunks_size"]
        cache[ep] = np.asarray(pq.read_table(os.path.join(RAW, info["data_path"].format(episode_chunk=c, episode_index=ep)))
                               .column("observation.state").to_pylist(), float)
    st = cache[ep]
    if k >= len(st):
        continue
    q = {n: float(v) for n, v in zip(names, st[k]) if n in m.joints}
    P = m.poses(q, base="arm_base_link")
    X = np.concatenate([(pts[l] @ P[l].T)[:, :3] for l in pts])
    g = np.load(os.path.join(MASKS, f"ep{ep:06d}_f{k:04d}.npz"))["m"].astype(np.uint8)
    if g.sum() < 200:
        continue
    edge = cv2.morphologyEx(g, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    dt_edge = cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 3)
    ys, xs = np.nonzero(edge)
    frames.append({"ep": ep, "k": k, "X": X, "g": g.astype(bool), "dt_edge": dt_edge, "edge": np.c_[xs, ys],
                   "img": it["img"]})
eps = sorted({f["ep"] for f in frames})
test_eps = set(np.random.default_rng(0).permutation(eps)[: len(eps) // 5].tolist())
train = [f for f in frames if f["ep"] not in test_eps][::5]  # optimiser subset (CPU time)
test = [f for f in frames if f["ep"] in test_eps]


def cam(th):
    E = np.eye(4)
    E[:3, :3] = C._rodrigues(th[:3])
    E[:3, 3] = th[3:6]
    K = K0.copy()
    K[0, 0] = K[1, 1] = K0[0, 0] * np.exp(th[6])
    return E, K


def sil(f, E, K):
    uv = C.project_many(K, E, f["X"])
    ok = np.isfinite(uv).all(1) & (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
    s = np.zeros((H, W), np.uint8)
    u = uv[ok].astype(int)
    s[u[:, 1], u[:, 0]] = 1
    s = cv2.morphologyEx(cv2.dilate(s, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return s, ok.mean()


def frame_err(f, E, K):
    s, vis = sil(f, E, K)
    if vis < 0.3 or s.sum() < 50:
        return None
    se = cv2.morphologyEx(s, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    near = cv2.dilate(s, np.ones((2 * NEAR + 1, 2 * NEAR + 1), np.uint8)) > 0
    ys, xs = np.nonzero(se)
    a = np.minimum(f["dt_edge"][ys, xs], TR)  # silhouette boundary -> mask boundary
    dts = cv2.distanceTransform((~se).astype(np.uint8), cv2.DIST_L2, 3)
    e = f["edge"][near[f["edge"][:, 1], f["edge"][:, 0]]]
    b = np.minimum(dts[e[:, 1], e[:, 0]], TR) if len(e) else np.array([TR])
    gm = f["g"] & near
    iou = float((gm & (s > 0)).sum() / max(1, (gm | (s > 0)).sum()))
    return float(np.median(np.r_[a, b])), float(a.mean() + b.mean()), iou


def total(th, fs):
    E, K = cam(th)
    v = [frame_err(f, E, K) for f in fs]
    return float(np.mean([x[1] if x else 2 * TR for x in v]))


def held(th, fs):
    E, K = cam(th)
    v = [x for x in (frame_err(f, E, K) for f in fs) if x]
    ch = np.array([x[0] for x in v])
    return {"frames": len(v), "boundary_chamfer_median_px": round(float(np.median(ch)), 2),
            "chamfer_le5px_frames": round(float(np.mean(ch <= 5)), 3), "iou_median": round(float(np.median([x[2] for x in v])), 3)}


def th_of(E, K):
    return np.r_[C._rvec(E[:3, :3]), E[:3, 3], np.log(K[0, 0] / K0[0, 0])]


res = {"frames": len(frames), "train": len(train), "test": len(test)}
best = None
for sp in STARTS:
    z = np.load(sp)
    Ek, Kk = (z["E"], z["K"]) if "E" in z.files else (z["track_E"], z["track_K"])
    th0 = th_of(Ek, Kk)
    name = os.path.basename(sp).replace(".npz", "")
    th0[6] = 0.0  # focal fixed to the ZED Mini VGA spec (367 px): 6-DoF only
    r = minimize(lambda t6, fs: total(np.r_[t6, 0.0], fs), th0[:6], args=(train,), method="Nelder-Mead", options={"maxiter": 900, "xatol": 1e-5, "fatol": 1e-3})
    r.x = np.r_[r.x, 0.0]
    E, K = cam(r.x)
    res[name] = {"start_heldout": held(th0, test), "fit_heldout": held(r.x, test), "train_cost": round(float(r.fun), 3),
                 "fx": round(float(K[0, 0]), 1), "iters": int(r.nit)}
    np.savez(OUTP.replace(".json", f"_{name}.npz"), E=E, K=K)
    if best is None or r.fun < best[0]:
        best = (r.fun, r.x, name)
    tiles = []
    for f in test[:12]:
        im = cv2.imread(f["img"])
        s, _ = sil(f, E, K)
        cs, _ = cv2.findContours(s, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(im, cs, -1, (0, 0, 255), 1)
        cg, _ = cv2.findContours(f["g"].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(im, cg, -1, (0, 255, 255), 1)
        tiles.append(im)
    while len(tiles) % 3:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(OUTP.replace(".json", f"_{name}.jpg"), np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]))
# synthetic: masks from the best camera, recover from a perturbed start
Eb, Kb = cam(best[1])
syn = []
for f in train[:30]:
    s, _ = sil(f, Eb, Kb)
    edge = cv2.morphologyEx(s, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    ys, xs = np.nonzero(edge)
    syn.append(dict(f, g=s.astype(bool), dt_edge=cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 3),
                    edge=np.c_[xs, ys]))
thp = best[1] + np.r_[np.radians([2, -2, 1.5]), [0.04, -0.03, 0.05], [0.0]]
r = minimize(lambda t6, fs: total(np.r_[t6, 0.0], fs), thp[:6], args=(syn,), method="Nelder-Mead", options={"maxiter": 900, "xatol": 1e-5, "fatol": 1e-4})
r.x = np.r_[r.x, 0.0]
Es, Ks = cam(r.x)
rot, dist = C.pose_error(Es, Eb)
res["synthetic_recover"] = {"rot_deg": round(rot, 3), "centre_cm": round(dist * 100, 2),
                            "fx_pct": round(float(Ks[0, 0] / Kb[0, 0] - 1) * 100, 2), "heldout_vs_truth": held(r.x, syn)}
json.dump(res, open(OUTP, "w"), indent=1)
print(json.dumps(res, indent=1))
