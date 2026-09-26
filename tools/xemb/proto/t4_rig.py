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
    g = np.load(it["mask"])["m"].astype(np.uint8)
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
    r = minimize(total, th0, args=(fs,), method="Nelder-Mead", options={"maxiter": 700, "xatol": 1e-5, "fatol": 1e-3})
    return r.x


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
    th = fit(th_of(E0), tr)
    E = cam(th)
    held = [ferr(f, E) for f in ts]
    res["start_nominal_heldout_median_px"] = round(float(np.median([x[0] for x in start if x])), 2)
    np.savez(OUTP.replace(".json", ".npz"), E_head=E, K=K)
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
json.dump(res, open(OUTP, "w"), indent=1)
print(json.dumps(res, indent=1))
