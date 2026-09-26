"""RB2 head stereo -> metric depth with Fast-FoundationStereo (NVIDIA, arXiv 2512.11130; weights
nvidia/c-fast-foundationstereo, NVIDIA Open Model Agreement), gated against the T4 camera:
  arm gate    stereo depth vs the z-buffered depth of the URDF arm + gripper meshes (FK from the joint encoders,
              T4 silhouette-aligned camera) on pixels that are both mesh and SAM 'robot arm' mask; per frame median
              |dz| and signed median (baseline / scale bias)
  table gate  RANSAC plane on non-arm pixels of the lower image -> base frame: tilt from base z and height; spread
              over frames (one fixed table)
Left = cam_head, right = cam_head_right (ZED Mini, rectified by the ZED driver; baseline 63 mm by spec).
usage: ffs_rb2.py MASK_DIR CAM_NPZ OUT_DIR [N_FRAMES]   (uv python 3.12 + venv_sam3 site + pylib_ffs)"""
import json, os, sys
import site
site.addsitedir("/data/harvest/venv_sam3/lib/python3.12/site-packages")
site.addsitedir("/data/harvest/pylib_ffs")
FFS = "/data/harvest/out/xemb_proto/ffs"
sys.path.insert(0, FFS)
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
import av
import cv2
import numpy as np
import pyarrow.parquet as pq
import torch
import trimesh
from core.utils.utils import InputPadder
from Utils import AMP_DTYPE
from xemb import urdf_fk as U

MASKS, CAM, OUT = sys.argv[1:4]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
RAW = "/data/harvest/data/se2e/raw/Task_0002_OrderPicking_lerobot"
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
MESH_ROOT = "/data/harvest/tmp/ai_worker"
BASELINE = float(os.environ.get("FFS_BASELINE", "0.063"))
GATE_CM = 2.0
os.makedirs(os.path.join(OUT, "depth"), exist_ok=True)
z4 = np.load(CAM)
E, K = z4["E"], z4["K"]
fx = float(K[0, 0])
m = U.Urdf(URDF)
LINKS = [f"gripper_{s}_rh_p12_rn_{p}" for s in "lr" for p in ("base", "r1", "r2", "l1", "l2")] + \
    [f"arm_{s}_link{i}" for s in "lr" for i in range(1, 8)]
pts = {}
for v in m.visuals():
    if v["link"] in LINKS:
        mesh = trimesh.load(v["file"].replace("package://", MESH_ROOT + "/"), force="mesh")
        p = mesh.sample(30000, seed=0) * np.asarray(v["scale"])
        pts[v["link"]] = np.c_[p, np.ones(len(p))] @ v["T"].T
info = json.load(open(os.path.join(RAW, "meta", "info.json")))
names = info["features"]["observation.state"]["names"]
model = torch.load(os.path.join(FFS, "weights/c_ffs/model_best_bp2_serialize.pth"), map_location="cpu", weights_only=False)
model.args.valid_iters = 8
model.args.max_disp = 192
if "normalize" not in model.args:  # the NVIDIA c-FFS checkpoint predates this arg; code default is True
    model.args.normalize = True
model.cuda().eval()
torch.autograd.set_grad_enabled(False)


def frame(ep, key, k):
    c = ep // info["chunks_size"]
    p = os.path.join(RAW, info["video_path"].format(episode_chunk=c, video_key=key, episode_index=ep))
    if not os.path.exists(p):  # some episodes have no right-camera video
        return None
    with av.open(p) as cont:
        for i, fr in enumerate(cont.decode(video=0)):
            if i == k:
                return fr.to_ndarray(format="rgb24")
    return None


def stereo(l, r):
    a = torch.as_tensor(l).cuda().float()[None].permute(0, 3, 1, 2)
    b = torch.as_tensor(r).cuda().float()[None].permute(0, 3, 1, 2)
    pad = InputPadder(a.shape, divis_by=32, force_square=False)
    a, b = pad.pad(a, b)
    with torch.amp.autocast("cuda", enabled=True, dtype=AMP_DTYPE):
        d = model.forward(a, b, iters=8, test_mode=True, optimize_build_volume="pytorch1")
    d = pad.unpad(d.float()).cpu().numpy().reshape(l.shape[:2]).clip(0, None)
    return d


def zbuf(X, H, W):
    Xc = X @ E[:3, :3].T + E[:3, 3]
    ok = Xc[:, 2] > 0.05
    Xc = Xc[ok]
    u = (K[0, 0] * Xc[:, 0] / Xc[:, 2] + K[0, 2]).astype(int)
    v = (K[1, 1] * Xc[:, 1] / Xc[:, 2] + K[1, 2]).astype(int)
    ok = (u >= 0) & (u < W) & (v >= 0) & (v < H)
    zb = np.full((H, W), np.inf)
    np.minimum.at(zb, (v[ok], u[ok]), Xc[ok, 2])
    zb = cv2.erode(np.where(np.isfinite(zb), zb, 1e3).astype(np.float32), np.ones((3, 3), np.uint8))  # 3x3 min fills holes
    zb[zb >= 999] = np.inf
    return zb


def plane(P, it=300, tol=0.01, rng=np.random.default_rng(0)):
    best, bi = None, 0
    for _ in range(it):
        s = P[rng.choice(len(P), 3, replace=False)]
        n = np.cross(s[1] - s[0], s[2] - s[0])
        if np.linalg.norm(n) < 1e-9:
            continue
        n /= np.linalg.norm(n)
        d = -n @ s[0]
        inl = np.abs(P @ n + d) < tol
        if inl.sum() > bi:
            best, bi = (n, d), inl.sum()
    return best, bi / len(P)


idx = json.load(open(os.path.join(MASKS, "index.json")))[:N]
Tbc = np.linalg.inv(E)
rows, cache = [], {}
for it in idx:
    ep, k = it["ep"], it["k"]
    mp = os.path.join(MASKS, f"ep{ep:06d}_f{k:04d}.npz")
    if not os.path.exists(mp):
        continue
    l, r = frame(ep, "observation.images.cam_head", k), frame(ep, "observation.images.cam_head_right", k)
    if l is None or r is None:
        continue
    H, W = l.shape[:2]
    disp = stereo(l, r)
    depth = np.where(disp > 0.5, fx * BASELINE / np.maximum(disp, 1e-3), np.inf)
    if ep not in cache:
        c = ep // info["chunks_size"]
        cache[ep] = np.asarray(pq.read_table(os.path.join(RAW, info["data_path"].format(episode_chunk=c, episode_index=ep)))
                               .column("observation.state").to_pylist(), float)
    q = {n: float(v) for n, v in zip(names, cache[ep][k]) if n in m.joints}
    P = m.poses(q, base="arm_base_link")
    X = np.concatenate([(pts[lk] @ P[lk].T)[:, :3] for lk in pts])
    zb = zbuf(X, H, W)
    g = np.load(mp)["m"].astype(bool)
    sel = g & np.isfinite(zb) & np.isfinite(depth)
    row = {"ep": ep, "k": k, "arm_px": int(sel.sum())}
    if sel.sum() >= 200:
        dz = depth[sel] - zb[sel]
        row.update(arm_abs_median_cm=round(float(np.median(np.abs(dz))) * 100, 2),
                   arm_signed_median_cm=round(float(np.median(dz)) * 100, 2),
                   arm_ratio_median=round(float(np.median(depth[sel] / zb[sel])), 4))
    # table: non-arm pixels in the lower 45 % of the image, 0.3-2.0 m
    vv, uu = np.mgrid[0:H, 0:W]
    tsel = (~cv2.dilate(g.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)) & (vv > 0.55 * H) & \
        np.isfinite(depth) & (depth > 0.3) & (depth < 2.0)
    if tsel.sum() > 500:
        z = depth[tsel]
        Pc = np.c_[(uu[tsel] - K[0, 2]) * z / K[0, 0], (vv[tsel] - K[1, 2]) * z / K[1, 1], z]
        Pb = Pc @ Tbc[:3, :3].T + Tbc[:3, 3]
        pl, frac = plane(Pb[np.random.default_rng(1).permutation(len(Pb))[:5000]])
        if pl is not None:
            n, d = pl
            n, d = (n, d) if n[2] > 0 else (-n, -d)
            row.update(table_tilt_deg=round(float(np.degrees(np.arccos(np.clip(n[2], -1, 1)))), 2),
                       table_height_m=round(float(-d / n[2]), 4), table_inlier_frac=round(float(frac), 3))
    row["pass"] = bool(row.get("arm_abs_median_cm", 99) <= GATE_CM)
    if row["pass"]:
        np.savez_compressed(os.path.join(OUT, "depth", f"ep{ep:06d}_f{k:04d}.npz"),
                            depth=np.where(np.isfinite(depth), depth, 0).astype(np.float16))
    rows.append(row)
    if len(rows) <= 3:
        vis = np.clip(0.4 / np.where(np.isfinite(depth), depth, 99), 0, 1)
        cv2.imwrite(os.path.join(OUT, f"vis_ep{ep}_f{k}.jpg"),
                    np.hstack([l[:, :, ::-1], cv2.applyColorMap((vis * 255).astype(np.uint8), cv2.COLORMAP_TURBO)]))
json.dump(rows, open(os.path.join(OUT, "rows.json"), "w"))
a = np.array([r["arm_abs_median_cm"] for r in rows if "arm_abs_median_cm" in r])
s = np.array([r["arm_signed_median_cm"] for r in rows if "arm_signed_median_cm" in r])
th = np.array([r["table_height_m"] for r in rows if "table_height_m" in r])
tt = np.array([r["table_tilt_deg"] for r in rows if "table_tilt_deg" in r])
rep = {"frames": len(rows), "baseline_m": BASELINE, "gate_cm": GATE_CM,
       "arm_abs_median_cm": {"median": round(float(np.median(a)), 2), "p90": round(float(np.percentile(a, 90)), 2),
                             "n": int(len(a))} if len(a) else None,
       "arm_signed_median_cm_median": round(float(np.median(s)), 2) if len(s) else None,
       "pass_frames": int(sum(r["pass"] for r in rows)),
       "table": {"height_m_median": round(float(np.median(th)), 4), "height_cm_iqr": round(float(np.subtract(
           *np.percentile(th, [75, 25]))) * 100, 2), "tilt_deg_median": round(float(np.median(tt)), 2),
           "n": int(len(th))} if len(th) else None}
json.dump(rep, open(os.path.join(OUT, "report.json"), "w"), indent=1)
print(json.dumps(rep, indent=1))
