"""T4 on more AI Worker rigs (RB1 CoffeeClassification, RB3 pickup_obj; ROBOTIS open data): silhouette boundary alignment
of the head camera, focal fixed to the ZED Mini VGA spec. If the state carries head joints (RB3), the camera is solved
ONCE in the head link frame (moves with the head); otherwise (RB1) per episode in arm_base_link (the head pose of RB1
differs between episodes, readiness 4.2), fit on 3 frames and tested on the held-out 4th.
usage: t4_rig.py MASK_INDEX RAW_ROOT TAG OUT_JSON"""
import json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
sys.path.append("/data/harvest/pylib_moge")
import cv2
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.optimize import minimize
from xemb import selfcal as C
from xemb import urdf_fk as U
from harvest.train import se2e_trace as TT

IDX, RAW, TAG, OUTP = sys.argv[1:5]
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
MESH_ROOT = "/data/harvest/tmp/ai_worker"
W, H = 672, 376
K = np.array([[367.0, 0, 336.0], [0, 367.0, 188.0], [0, 0, 1]])
LINKS = [f"gripper_{s}_rh_p12_rn_{p}" for s in "lr" for p in ("base", "r1", "r2", "l1", "l2")] + \
    [f"arm_{s}_link{i}" for s in "lr" for i in (4, 5, 6, 7)]
TR, NEAR = 30.0, 60
m = U.Urdf(URDF)
pts = {}
for v in m.visuals():
    if v["link"] in LINKS:
        mesh = trimesh.load(v["file"].replace("package://", MESH_ROOT + "/"), force="mesh")
        p = mesh.sample(1500 if "gripper" in v["link"] else 1000, seed=0) * np.asarray(v["scale"])
        pts[v["link"]] = np.c_[p, np.ones(len(p))] @ v["T"].T
info = json.load(open(os.path.join(RAW, "meta", "info.json")))
names = info["features"]["observation.state"]["names"]
has_head = "head_joint1" in names
cam_nom = TT.head_camera(TT.load_head_chain(URDF), TT.RB1_HEAD)
E_nom = np.eye(4)
E_nom[:3, :3] = cam_nom[0].T
E_nom[:3, 3] = -cam_nom[0].T @ cam_nom[1]
P_head_nom = m.poses({"head_joint1": TT.RB1_HEAD[0], "head_joint2": TT.RB1_HEAD[1]}, base="arm_base_link")["head_link2"]
frames, cache = [], {}
for it in json.load(open(IDX)):
    if it["tag"] != TAG:
        continue
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
    if has_head:  # express the points in the head link frame: the camera is fixed there
        X = C.project_many(np.eye(3), np.eye(4), X) if False else (np.c_[X, np.ones(len(X))] @ np.linalg.inv(P["head_link2"]).T)[:, :3]
    z = np.load(it["mask"])
    g = z[os.environ.get("T4_MASKKEY", "m")].astype(np.uint8)
    if os.environ.get("T4_MASKGATE") == "text" and (g.astype(bool) & z["m_text"]).sum() < 0.3 * max(1, g.sum()):
        continue  # box mask not confirmed by the text-only 'robot arm' detection (arm out of view -> junk)
    if g.sum() < 200:
        continue
    edge = cv2.morphologyEx(g, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    ys, xs = np.nonzero(edge)
    frames.append({"ep": ep, "k": k, "X": X, "g": g.astype(bool), "img": it["img"], "edge": np.c_[xs, ys],
                   "dt_edge": cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 3)})


def cam(th):
    E = np.eye(4)
    E[:3, :3] = C._rodrigues(th[:3])
    E[:3, 3] = th[3:6]
    return E


def sil(f, E):
    uv = C.project_many(K, E, f["X"])
    ok = np.isfinite(uv).all(1) & (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
    s = np.zeros((H, W), np.uint8)
    u = uv[ok].astype(int)
    s[u[:, 1], u[:, 0]] = 1
    s = cv2.morphologyEx(cv2.dilate(s, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return s, ok.mean()


def ferr(f, E):
    s, vis = sil(f, E)
    if vis < 0.3 or s.sum() < 50:
        return None
    se = cv2.morphologyEx(s, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    near = cv2.dilate(s, np.ones((2 * NEAR + 1, 2 * NEAR + 1), np.uint8)) > 0
    ys, xs = np.nonzero(se)
    a = np.minimum(f["dt_edge"][ys, xs], TR)
    dts = cv2.distanceTransform((~se).astype(np.uint8), cv2.DIST_L2, 3)
    e = f["edge"][near[f["edge"][:, 1], f["edge"][:, 0]]]
    b = np.minimum(dts[e[:, 1], e[:, 0]], TR) if len(e) else np.array([TR])
    iou = float(((f["g"] & near) & (s > 0)).sum() / max(1, ((f["g"] & near) | (s > 0)).sum()))
    return float(np.median(np.r_[a, b])), float(a.mean() + b.mean()), iou


def total(th, fs):
    E = cam(th)
    v = [ferr(f, E) for f in fs]
    return float(np.mean([x[1] if x else 2 * TR for x in v]))


def fit(th0, fs):
    # Nelder-Mead restarted from its own result (fresh simplex) until it stops improving: a single run stalled in a
    # poor local minimum on RB3 (7.0 px held-out, while bootstrap refits started from it reached 2.3 px)
    x, best = np.asarray(th0, float), np.inf
    for _ in range(int(os.environ.get("T4_RESTARTS", "1"))):
        r = minimize(total, x, args=(fs,), method="Nelder-Mead", options={"maxiter": 700, "xatol": 1e-5, "fatol": 1e-3})
        if r.fun >= best - 1e-3:
            break
        x, best = r.x, r.fun
    return x


def th_of(E):
    return np.r_[C._rvec(E[:3, :3]), E[:3, 3]]


res = {"tag": TAG, "frames": len(frames), "has_head_joints": has_head}
held = []
if has_head or os.environ.get("T4_GLOBAL") == "1":
    E0 = E_nom @ P_head_nom if has_head else E_nom  # cam <- head_link2 (head joints) or arm_base_link (one camera per dataset)
    eps = sorted({f["ep"] for f in frames})
    te = set(np.random.default_rng(0).permutation(eps)[: len(eps) // 5].tolist())
    tr = [f for f in frames if f["ep"] not in te][::2]
    ts = [f for f in frames if f["ep"] in te]
    start = [ferr(f, E0) for f in ts]
    if os.environ.get("T4_EINIT"):  # reuse a global fit (same split, seed 0)
        th = th_of(np.load(os.environ["T4_EINIT"])["E_head"])
    else:
        th = fit(th_of(E0), tr)
    E = cam(th)
    held = [ferr(f, E) for f in ts]
    if os.environ.get("T4_EPROT") == "1":
        # head pan/tilt is not in the state and may change between episodes: per held-out episode, refine only a
        # small camera rotation (3 DoF about the camera centre) on its first frames, test on its last frame
        g_last, r_last = [], []
        per_ts = {}
        for f in ts:
            per_ts.setdefault(f["ep"], []).append(f)
        for ep, fs in per_ts.items():
            fs = sorted(fs, key=lambda f: f["k"])
            if len(fs) < 2:
                continue

            def rot_err(d, fs=fs[:-1]):
                Rd = C._rodrigues(d)
                E2 = E.copy()
                E2[:3, :3], E2[:3, 3] = Rd @ E[:3, :3], Rd @ E[:3, 3]
                v = [ferr(f, E2) for f in fs]
                return float(np.mean([x[1] if x else 2 * TR for x in v]))
            r = minimize(rot_err, np.zeros(3), method="Nelder-Mead", options={"maxiter": 300, "xatol": 1e-5})
            Rd = C._rodrigues(r.x)
            E2 = E.copy()
            E2[:3, :3], E2[:3, 3] = Rd @ E[:3, :3], Rd @ E[:3, 3]
            g_last.append(ferr(fs[-1], E))
            r_last.append(ferr(fs[-1], E2))
        gv = np.array([x[0] for x in g_last if x])
        res["eprot_global_only_last_frame_median_px"] = round(float(np.median(gv)), 2) if len(gv) else None
        res["eprot_global_only_last_le5px"] = round(float(np.mean(gv <= 5)), 3) if len(gv) else None
        held = r_last
    res["start_nominal_heldout_median_px"] = round(float(np.median([x[0] for x in start if x])), 2)
    np.savez(OUTP.replace(".json", ".npz"), E_head=E, K=K)
    # pose ambiguity: refit on bootstrap resamples of the TRAINING episodes, compare the camera centre / axes
    boots, rng = [], np.random.default_rng(1)
    tr_eps = sorted({f["ep"] for f in tr})
    for b in range(int(os.environ.get("T4_BOOT", "0"))):
        pick = rng.choice(tr_eps, len(tr_eps), replace=True)
        fs = [f for e in pick for f in tr if f["ep"] == e]
        Eb = cam(fit(th, fs))
        dR = Eb[:3, :3] @ E[:3, :3].T
        c, cb = -E[:3, :3].T @ E[:3, 3], -Eb[:3, :3].T @ Eb[:3, 3]
        hb = np.array([x[0] for x in (ferr(f, Eb) for f in ts) if x])
        boots.append({"rot_deg": round(float(np.degrees(np.arccos(np.clip((np.trace(dR) - 1) / 2, -1, 1)))), 2),
                      "centre_cm": round(float(np.linalg.norm(c - cb) * 100), 2),
                      "heldout_median_px": round(float(np.median(hb)), 2) if len(hb) else None})
    if boots:
        res["bootstrap_train_eps"] = boots
else:
    per = {}
    for f in frames:
        per.setdefault(f["ep"], []).append(f)
    starts = []
    for ep, fs in per.items():
        if len(fs) < 3:
            continue
        tr, ts = fs[:-1], fs[-1:]
        starts += [ferr(f, E_nom) for f in ts]
        th = fit(th_of(E_nom), tr)
        held += [ferr(f, cam(th)) for f in ts]
    res["start_nominal_heldout_median_px"] = round(float(np.median([x[0] for x in starts if x])), 2)
v = np.array([x[0] for x in held if x])
res["heldout_frames"] = int(len(v))
res["heldout_boundary_chamfer_median_px"] = round(float(np.median(v)), 2) if len(v) else None
res["heldout_le5px_frames"] = round(float(np.mean(v <= 5)), 3) if len(v) else None
res["heldout_iou_median"] = round(float(np.median([x[2] for x in held if x])), 3) if len(v) else None
if len(v):  # 95 % interval of the held-out median and pass rate, bootstrap over held-out frames
    rb = np.random.default_rng(2)
    bs = [rb.choice(v, len(v)) for _ in range(2000)]
    res["heldout_median_ci95"] = [round(float(x), 2) for x in np.percentile([np.median(b) for b in bs], [2.5, 97.5])]
    res["heldout_le5px_ci95"] = [round(float(x), 3) for x in np.percentile([np.mean(b <= 5) for b in bs], [2.5, 97.5])]
json.dump(res, open(OUTP, "w"), indent=1)
print(json.dumps(res, indent=1))
