"""RB2 stereo depth for every frame used by the rb2t4 samples (Fast-FoundationStereo, c-FFS weights). Gate without SAM
masks: per-frame median |stereo - mesh z-buffer| over ALL pixels the URDF arm + gripper meshes cover (T4 camera);
occlusion (people, held objects) can only raise it, so the gate is conservative. Episodes are decoded once, in order.
Saves depth (float16, m) for frames passing GATE_CM, plus rows.json / report.json.
usage: ffs_rb2_prod.py CAM_NPZ OUT_DIR RECORDS_JSONL [RECORDS_JSONL ...]"""
import json, os, re, sys
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

CAM, OUT = sys.argv[1:3]
RAW = "/data/harvest/data/se2e/raw/Task_0002_OrderPicking_lerobot"
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
MESH_ROOT = "/data/harvest/tmp/ai_worker"
BASELINE, GATE_CM = 0.063, 2.0
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
model.args.valid_iters, model.args.max_disp = 8, 192
if "normalize" not in model.args:
    model.args.normalize = True
model.cuda().eval()
torch.autograd.set_grad_enabled(False)
PAT = re.compile(r"RB2/ep(\d+)/f(\d+)\.jpg")
want = {}
for rp in sys.argv[3:]:
    for line in open(rp, encoding="utf-8"):
        for im in json.loads(line).get("images", []):
            mm = PAT.search(im)
            if mm:
                want.setdefault(int(mm.group(1)), set()).add(int(mm.group(2)))


def vpath(ep, key):
    return os.path.join(RAW, info["video_path"].format(episode_chunk=ep // info["chunks_size"], video_key=key,
                                                        episode_index=ep))


def frames(p, ks):
    out = {}
    with av.open(p) as c:
        for i, fr in enumerate(c.decode(video=0)):
            if i in ks:
                out[i] = fr.to_ndarray(format="rgb24")
            if i >= max(ks):
                break
    return out


def stereo(l, r):
    a = torch.as_tensor(l).cuda().float()[None].permute(0, 3, 1, 2)
    b = torch.as_tensor(r).cuda().float()[None].permute(0, 3, 1, 2)
    pad = InputPadder(a.shape, divis_by=32, force_square=False)
    a, b = pad.pad(a, b)
    with torch.amp.autocast("cuda", enabled=True, dtype=AMP_DTYPE):
        d = model.forward(a, b, iters=8, test_mode=True, optimize_build_volume="pytorch1")
    return pad.unpad(d.float()).cpu().numpy().reshape(l.shape[:2]).clip(0, None)


def zbuf(X, H, W):
    Xc = X @ E[:3, :3].T + E[:3, 3]
    Xc = Xc[Xc[:, 2] > 0.05]
    u = (K[0, 0] * Xc[:, 0] / Xc[:, 2] + K[0, 2]).astype(int)
    v = (K[1, 1] * Xc[:, 1] / Xc[:, 2] + K[1, 2]).astype(int)
    ok = (u >= 0) & (u < W) & (v >= 0) & (v < H)
    zb = np.full((H, W), 1e3, np.float32)
    np.minimum.at(zb, (v[ok], u[ok]), Xc[ok, 2].astype(np.float32))
    zb = cv2.erode(zb, np.ones((3, 3), np.uint8))
    zb[zb >= 999] = np.inf
    return zb


rows = []
for ep in sorted(want):
    pl, pr = vpath(ep, "observation.images.cam_head"), vpath(ep, "observation.images.cam_head_right")
    if not (os.path.exists(pl) and os.path.exists(pr)):
        continue
    ks = want[ep]
    L, R = frames(pl, ks), frames(pr, ks)
    st = np.asarray(pq.read_table(os.path.join(RAW, info["data_path"].format(
        episode_chunk=ep // info["chunks_size"], episode_index=ep))).column("observation.state").to_pylist(), float)
    for k in sorted(ks):
        if k not in L or k not in R or k >= len(st):
            continue
        l, r = L[k], R[k]
        H, W = l.shape[:2]
        disp = stereo(l, r)
        depth = np.where(disp > 0.5, fx * BASELINE / np.maximum(disp, 1e-3), np.inf)
        q = {n: float(x) for n, x in zip(names, st[k]) if n in m.joints}
        P = m.poses(q, base="arm_base_link")
        zb = zbuf(np.concatenate([(pts[lk] @ P[lk].T)[:, :3] for lk in pts]), H, W)
        sel = np.isfinite(zb) & np.isfinite(depth)
        row = {"ep": ep, "k": k, "mesh_px": int(sel.sum())}
        if sel.sum() >= 200:
            dz = depth[sel] - zb[sel]
            row.update(abs_median_cm=round(float(np.median(np.abs(dz))) * 100, 2),
                       signed_median_cm=round(float(np.median(dz)) * 100, 2))
        row["pass"] = bool(row.get("abs_median_cm", 99) <= GATE_CM)
        if row["pass"]:
            np.savez_compressed(os.path.join(OUT, "depth", f"ep{ep:06d}_f{k:04d}.npz"),
                                depth=np.where(np.isfinite(depth), depth, 0).astype(np.float16))
        rows.append(row)
    if len(rows) and len(rows) % 500 < len(ks):
        print("frames", len(rows), "pass", sum(r["pass"] for r in rows), flush=True)
json.dump(rows, open(os.path.join(OUT, "rows.json"), "w"))
a = np.array([r["abs_median_cm"] for r in rows if "abs_median_cm" in r])
rep = {"frames": len(rows), "episodes": len({r["ep"] for r in rows}), "gate_cm": GATE_CM,
       "abs_median_cm": {"median": round(float(np.median(a)), 2), "p90": round(float(np.percentile(a, 90)), 2)},
       "signed_median_cm": round(float(np.median([r["signed_median_cm"] for r in rows if "signed_median_cm" in r])), 2),
       "pass_frames": int(sum(r["pass"] for r in rows)), "no_mesh_in_view": int(sum("abs_median_cm" not in r for r in rows))}
json.dump(rep, open(os.path.join(OUT, "report.json"), "w"), indent=1)
print(json.dumps(rep, indent=1))
