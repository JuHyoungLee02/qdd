"""Per-frame T4 verification for generated samples: the head may move within an episode (RB3 state has no head joints),
so every sample frame is checked: boundary chamfer between the projected arm+gripper mesh silhouette (T4 camera) and
the SAM 3.1 box-prompted arm mask (text-confirmed), frame kept if <= GATE_PX. Filters records_P / records_C.
usage: t4_verify.py frames RECORDS_DIR TAG OUT_FRAMES_JSON            (list sample frames)
       t4_verify.py check RAW_ROOT CAM_NPZ MASK_INDEX RECORDS_DIR OUT_DIR"""
import json, os, re, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
sys.path.append("/data/harvest/pylib_moge")
import numpy as np

PAT = re.compile(r"_ep(\d+)_f(\d+)\.jpg$")
if sys.argv[1] == "frames":
    d, tag, outp = sys.argv[2:5]
    seen = {}
    for name in ("records_P.jsonl", "records_C.jsonl"):
        for line in open(os.path.join(d, name)):
            for im in json.loads(line)["images"]:
                m = PAT.search(im)
                seen[im] = {"tag": tag, "ep": int(m.group(1)), "k": int(m.group(2)), "img": im}
    json.dump(list(seen.values()), open(outp, "w"))
    print("frames", len(seen))
    sys.exit()

import cv2
import pyarrow.parquet as pq
import trimesh
from xemb import selfcal as C
from xemb import urdf_fk as U

RAW, CAM, IDX, RD, OUT = sys.argv[2:7]
GATE_PX, TR, NEAR = 5.0, 30.0, 60
W, H = 672, 376
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
MESH_ROOT = "/data/harvest/tmp/ai_worker"
z = np.load(CAM)
E, K = z["E_head"], z["K"]
LINKS = [f"gripper_{s}_rh_p12_rn_{p}" for s in "lr" for p in ("base", "r1", "r2", "l1", "l2")] + \
    [f"arm_{s}_link{i}" for s in "lr" for i in (4, 5, 6, 7)]
m = U.Urdf(URDF)
pts = {}
for v in m.visuals():
    if v["link"] in LINKS:
        mesh = trimesh.load(v["file"].replace("package://", MESH_ROOT + "/"), force="mesh")
        p = mesh.sample(1500 if "gripper" in v["link"] else 1000, seed=0) * np.asarray(v["scale"])
        pts[v["link"]] = np.c_[p, np.ones(len(p))] @ v["T"].T
info = json.load(open(os.path.join(RAW, "meta", "info.json")))
names = info["features"]["observation.state"]["names"]


def err(X, g):
    uv = C.project_many(K, E, X)
    ok = np.isfinite(uv).all(1) & (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
    if ok.mean() < 0.3:
        return None
    s = np.zeros((H, W), np.uint8)
    u = uv[ok].astype(int)
    s[u[:, 1], u[:, 0]] = 1
    s = cv2.morphologyEx(cv2.dilate(s, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    edge = cv2.morphologyEx(g, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    dt_edge = cv2.distanceTransform((~edge).astype(np.uint8), cv2.DIST_L2, 3)
    se = cv2.morphologyEx(s, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    near = cv2.dilate(s, np.ones((2 * NEAR + 1, 2 * NEAR + 1), np.uint8)) > 0
    ys, xs = np.nonzero(se)
    a = np.minimum(dt_edge[ys, xs], TR)
    dts = cv2.distanceTransform((~se).astype(np.uint8), cv2.DIST_L2, 3)
    ey, ex = np.nonzero(edge & near)
    b = np.minimum(dts[ey, ex], TR) if len(ey) else np.array([TR])
    return float(np.median(np.r_[a, b]))


res, cache = {}, {}
for it in json.load(open(IDX)):
    zz = np.load(it["mask"])
    g = zz["m"].astype(np.uint8)
    if g.sum() < 200 or (g.astype(bool) & zz["m_text"]).sum() < 0.3 * g.sum():
        res[it["img"]] = None
        continue
    ep, k = it["ep"], it["k"]
    if ep not in cache:
        cache[ep] = np.asarray(pq.read_table(os.path.join(RAW, info["data_path"].format(
            episode_chunk=ep // info["chunks_size"], episode_index=ep))).column("observation.state").to_pylist(), float)
    q = {n: float(x) for n, x in zip(names, cache[ep][k]) if n in m.joints}
    P = m.poses(q, base="arm_base_link")
    res[it["img"]] = err(np.concatenate([(pts[l] @ P[l].T)[:, :3] for l in pts]), g)
os.makedirs(OUT, exist_ok=True)
ok = {im for im, e in res.items() if e is not None and e <= GATE_PX}
cnt = {}
for name in ("records_P.jsonl", "records_C.jsonl"):
    n_in = n_out = 0
    with open(os.path.join(OUT, name), "w") as f:
        for line in open(os.path.join(RD, name)):
            r = json.loads(line)
            n_in += 1
            cam_unknown = "camera: unknown" in r["prompt"]
            if cam_unknown or all(im in ok for im in r["images"]):  # camera-unknown C' needs no camera
                f.write(line)
                n_out += 1
    cnt[name] = [n_in, n_out]
v = np.array([e for e in res.values() if e is not None])
rep = {"frames": len(res), "mask_ok": int(len(v)), "chamfer_median_px": round(float(np.median(v)), 2),
       "pass_le5px": len(ok), "pass_rate_of_all": round(len(ok) / max(1, len(res)), 3), "records_in_out": cnt}
json.dump(rep, open(os.path.join(OUT, "verify.json"), "w"), indent=1)
json.dump(res, open(os.path.join(OUT, "frame_chamfer.json"), "w"))
print(json.dumps(rep, indent=1))
