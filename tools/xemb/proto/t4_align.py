"""T4 (CPU): URDF-mesh silhouette alignment of the RB2 head camera (CtRNet-X-style, point-sampled meshes, no GPU).
  model: AI Worker FFW-BG2 rev4 URDF + ROBOTIS ai_worker meshes (arms link3-7, grippers, torso), FK from the raw
         joint states (arms, grippers with mimic, head, lift), poses in arm_base_link;
  target: SAM 3.1 'robot arm' / 'robot gripper' masks (t4/masks);
  cost per frame: mean truncated distance-to-mask of the projected mesh points (in) + 0.5 x mean truncated distance
         from mask pixels to the projected points (coverage); camera = arm_base_link -> cam (6) + focal (1);
  init: the T1 track-based camera (or nominal); Nelder-Mead on the train frames, held-out frames by episode.
Also: a synthetic check (masks rasterised from a known camera, recover from a perturbed start).
usage: t4_align.py MASK_DIR OUT_JSON [T1_FIT_NPZ]"""
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

MASKS, OUTP = sys.argv[1], sys.argv[2]
T1 = sys.argv[3] if len(sys.argv) > 3 else None
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
MESH_ROOT = "/data/harvest/tmp/ai_worker"
RAW = "/data/harvest/data/se2e/raw/Task_0002_OrderPicking_lerobot"
W, H, S = 672, 376, 2  # optimise on half resolution
K0 = np.array([[367.0, 0, 336.0], [0, 367.0, 188.0], [0, 0, 1]])
USE = [f"arm_{s}_link{i}" for s in "lr" for i in (3, 4, 5, 6, 7)] + \
      [f"gripper_{s}_rh_p12_rn_{p}" for s in "lr" for p in ("base", "r1", "r2", "l1", "l2")]
GRIP = [f"gripper_{s}_rh_p12_rn_{p}" for s in "lr" for p in ("base", "r1", "r2", "l1", "l2")]
rng = np.random.default_rng(0)
m = U.Urdf(URDF)
pts_link = {}
for v in m.visuals():
    if v["link"] not in USE:
        continue
    f = v["file"].replace("package://", MESH_ROOT + "/")
    if not os.path.exists(f):
        continue
    mesh = trimesh.load(f, force="mesh")
    p = mesh.sample(200 if v["link"] in GRIP else 150, seed=0) * np.asarray(v["scale"])
    pts_link[v["link"]] = np.c_[p, np.ones(len(p))] @ v["T"].T
info = json.load(open(os.path.join(RAW, "meta", "info.json")))
names = info["features"]["observation.state"]["names"]
idx = json.load(open(os.path.join(MASKS, "index.json")))
frames = []
cache = {}
for it in idx:
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
    X = np.concatenate([(pts_link[l] @ P[l].T)[:, :3] for l in pts_link])
    G = np.concatenate([(pts_link[l] @ P[l].T)[:, :3] for l in pts_link if l in GRIP])
    mk = np.load(os.path.join(MASKS, f"ep{ep:06d}_f{k:04d}.npz"))["m"]
    if mk.sum() < 500:
        continue
    small = cv2.resize(mk.astype(np.uint8), (W // S, H // S), interpolation=cv2.INTER_NEAREST)
    dt_out = cv2.distanceTransform((1 - small).astype(np.uint8), cv2.DIST_L2, 3)
    ys, xs = np.nonzero(small)
    sel = rng.permutation(len(xs))[:800]
    frames.append({"ep": ep, "k": k, "X": X, "G": G, "dt": dt_out, "mpix": np.c_[xs[sel], ys[sel]].astype(float),
                   "img": it["img"], "mask": mk})
eps = sorted({f["ep"] for f in frames})
test_eps = set(np.random.default_rng(0).permutation(eps)[: len(eps) // 5].tolist())
train = [f for f in frames if f["ep"] not in test_eps][::3]  # 1 frame in 3 for the optimiser (speed)
test = [f for f in frames if f["ep"] in test_eps]
TRUNC = 30.0


def cam(theta):
    E = np.eye(4)
    E[:3, :3] = C._rodrigues(theta[:3])
    E[:3, 3] = theta[3:6]
    K = K0.copy()
    K[0, 0] = K[1, 1] = K0[0, 0] * np.exp(theta[6])
    return E, K


def frame_cost(f, E, K, which="X"):
    uv = C.project_many(K, E, f[which]) / S
    ok = np.isfinite(uv).all(1) & (uv[:, 0] >= 0) & (uv[:, 0] < W / S - 1) & (uv[:, 1] >= 0) & (uv[:, 1] < H / S - 1)
    if ok.mean() < 0.3:
        return TRUNC * 2, None
    u = uv[ok].astype(int)
    din = np.minimum(f["dt"][u[:, 1], u[:, 0]], TRUNC)
    # coverage: mask pixels -> nearest projected point (subsample)
    ras = np.zeros((H // S, W // S), np.uint8)
    ras[u[:, 1], u[:, 0]] = 1
    dtp = cv2.distanceTransform((1 - ras).astype(np.uint8), cv2.DIST_L2, 3)
    d = dtp[f["mpix"][:, 1].astype(int), f["mpix"][:, 0].astype(int)]
    return float(din.mean() + 0.5 * np.minimum(d, TRUNC).mean() + TRUNC * (1 - ok.mean())), din


def total(theta, fs):
    E, K = cam(theta)
    return float(np.mean([frame_cost(f, E, K)[0] for f in fs]))


def theta_of(E, K):
    return np.r_[C._rvec(E[:3, :3]), E[:3, 3], np.log(K[0, 0] / K0[0, 0])]


def held(theta, fs):
    E, K = cam(theta)
    din_all, grip = [], []
    for f in fs:
        _, din = frame_cost(f, E, K)
        _, dg = frame_cost(f, E, K, "G")
        if din is not None:
            din_all.append(np.median(din) * S)
        if dg is not None:
            grip.append(np.median(dg) * S)
    return {"frames": len(fs), "silhouette_in_median_px": round(float(np.median(din_all)), 2) if din_all else None,
            "gripper_points_to_mask_median_px": round(float(np.median(grip)), 2) if grip else None,
            "gripper_le5px_frames": round(float(np.mean(np.array(grip) <= 5)), 3) if grip else None}


res = {"frames": len(frames), "train": len(train), "test": len(test), "links": len(pts_link)}
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
from xemb import src_rb2 as R  # noqa: E402
En = R.nominal_E(URDF)
starts = {"nominal": theta_of(En, K0)}
if T1 and os.path.exists(T1):
    z = np.load(T1)
    starts["t1_track"] = theta_of(z["track_E"], z["track_K"])
for name, th0 in starts.items():
    res[f"start_{name}"] = {"train_cost": round(total(th0, train), 3), "heldout": held(th0, test)}
    r = minimize(total, th0, args=(train,), method="Nelder-Mead",
                 options={"maxiter": 1500, "xatol": 1e-4, "fatol": 1e-3, "initial_simplex": None})
    E, K = cam(r.x)
    rot, dist = C.pose_error(E, En)
    res[f"fit_from_{name}"] = {"train_cost": round(float(r.fun), 3), "fx": round(float(K[0, 0]), 1),
                               "vs_nominal": {"rot_deg": round(rot, 2), "centre_cm": round(dist * 100, 2)},
                               "heldout": held(r.x, test), "iters": int(r.nit)}
    np.savez(OUTP.replace(".json", f"_{name}.npz"), E=E, K=K)
    # overlay sheet of held-out frames
    tiles = []
    for f in test[:12]:
        im = cv2.imread(f["img"])
        cs, _ = cv2.findContours(f["mask"].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(im, cs, -1, (0, 255, 255), 1)
        for p in C.project_many(K, E, f["X"])[::3]:
            if np.isfinite(p).all():
                cv2.circle(im, (int(p[0]), int(p[1])), 1, (0, 0, 255), -1)
        for p in C.project_many(K, E, f["G"])[::2]:
            if np.isfinite(p).all():
                cv2.circle(im, (int(p[0]), int(p[1])), 1, (255, 0, 0), -1)
        tiles.append(cv2.resize(im, (448, 251)))
    while len(tiles) % 3:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(OUTP.replace(".json", f"_{name}.jpg"),
                np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]))
# synthetic check: masks rasterised from the fitted camera, recover from a perturbed start
best = min((k for k in res if k.startswith("fit_from_")), key=lambda k: res[k]["train_cost"])
Eb, Kb = [np.load(OUTP.replace(".json", f"_{best[9:]}.npz"))[x] for x in ("E", "K")]
syn = []
for f in train[:60]:
    uv = C.project_many(Kb, Eb, f["X"]) / S
    small = np.zeros((H // S, W // S), np.uint8)
    for p in uv[np.isfinite(uv).all(1)].astype(int):
        if 0 <= p[0] < W // S and 0 <= p[1] < H // S:
            cv2.circle(small, (int(p[0]), int(p[1])), 3, 1, -1)
    ys, xs = np.nonzero(small)
    sel = rng.permutation(len(xs))[:800]
    syn.append(dict(f, dt=cv2.distanceTransform((1 - small).astype(np.uint8), cv2.DIST_L2, 3),
                    mpix=np.c_[xs[sel], ys[sel]].astype(float)))
thb = theta_of(Eb, Kb)
th_p = thb + np.r_[np.radians([2, -2, 1.5]), [0.04, -0.03, 0.05], [0.08]]
r = minimize(total, th_p, args=(syn,), method="Nelder-Mead", options={"maxiter": 1500, "xatol": 1e-4, "fatol": 1e-4})
Es, Ks = cam(r.x)
rot, dist = C.pose_error(Es, Eb)
res["synthetic_recover"] = {"start_rot_deg": 3.2, "start_centre_cm": 7.1, "start_fx_pct": 8.3,
                            "rot_deg": round(rot, 3), "centre_cm": round(dist * 100, 2),
                            "fx_pct": round(float(Ks[0, 0] / Kb[0, 0] - 1) * 100, 2)}
json.dump(res, open(OUTP, "w"), indent=1)
print(json.dumps(res, indent=1))
