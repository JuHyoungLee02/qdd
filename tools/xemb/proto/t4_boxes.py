"""Per-frame arm boxes for box-prompted SAM (T4 on RB1/RB3): project the FK arm+gripper mesh points with the NOMINAL
URDF head camera (not the fitted one, so the mask is not built from the camera it will test), one xyxy box per arm,
padded by PAD px and clipped to the image. usage: t4_boxes.py FRAMES_JSON RAW_ROOT OUT_JSON"""
import json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
sys.path.append("/data/harvest/pylib_moge")
import numpy as np
import pyarrow.parquet as pq
import trimesh
from xemb import selfcal as C
from xemb import urdf_fk as U
from harvest.train import se2e_trace as TT

FR, RAW, OUTP = sys.argv[1:4]
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
MESH_ROOT = "/data/harvest/tmp/ai_worker"
W, H = 672, 376
PAD = int(os.environ.get("T4_PAD", "30"))
K = np.array([[367.0, 0, 336.0], [0, 367.0, 188.0], [0, 0, 1]])
LINKS = [f"gripper_{s}_rh_p12_rn_{p}" for s in "lr" for p in ("base", "r1", "r2", "l1", "l2")] + \
    [f"arm_{s}_link{i}" for s in "lr" for i in (4, 5, 6, 7)]
m = U.Urdf(URDF)
pts = {}
for v in m.visuals():
    if v["link"] in LINKS:
        mesh = trimesh.load(v["file"].replace("package://", MESH_ROOT + "/"), force="mesh")
        p = mesh.sample(600, seed=0) * np.asarray(v["scale"])
        pts[v["link"]] = np.c_[p, np.ones(len(p))] @ v["T"].T
cam = TT.head_camera(TT.load_head_chain(URDF), TT.RB1_HEAD)
E = np.eye(4)
E[:3, :3] = cam[0].T
E[:3, 3] = -cam[0].T @ cam[1]
info = json.load(open(os.path.join(RAW, "meta", "info.json")))
names = info["features"]["observation.state"]["names"]
cache, out = {}, []
for it in json.load(open(FR)):
    ep, k = it["ep"], it["k"]
    if ep not in cache:
        c = ep // info["chunks_size"]
        cache[ep] = np.asarray(pq.read_table(os.path.join(RAW, info["data_path"].format(episode_chunk=c, episode_index=ep)))
                               .column("observation.state").to_pylist(), float)
    if k >= len(cache[ep]):
        continue
    q = {n: float(v) for n, v in zip(names, cache[ep][k]) if n in m.joints}
    P = m.poses(q, base="arm_base_link")
    boxes = []
    for side in "lr":
        X = np.concatenate([(pts[l] @ P[l].T)[:, :3] for l in pts if f"_{side}_" in l])
        uv = C.project_many(K, E, X)
        uv = uv[np.isfinite(uv).all(1)]
        uv = uv[(uv[:, 0] > -W) & (uv[:, 0] < 2 * W) & (uv[:, 1] > -H) & (uv[:, 1] < 2 * H)]
        if len(uv) < 50:
            continue
        x0, y0 = np.clip(uv.min(0) - PAD, 0, [W - 1, H - 1])
        x1, y1 = np.clip(uv.max(0) + PAD, 0, [W - 1, H - 1])
        if (x1 - x0) > 20 and (y1 - y0) > 20:
            boxes.append([float(x0), float(y0), float(x1), float(y1)])
    out.append(dict(it, boxes=boxes))
json.dump(out, open(OUTP, "w"))
print("frames", len(out), "with boxes", sum(bool(o["boxes"]) for o in out), "links", len(pts))
