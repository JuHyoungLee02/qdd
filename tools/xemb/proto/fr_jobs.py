"""Franka hide-and-recover inputs (CPU): exocentric frames of 30 MolmoBot Franka episodes (camera fixed in the world,
base fixed) every 3rd frame, pointing jobs, and the GT (hidden) camera + measured TCP per frame.
usage: fr_jobs.py OUT"""
import json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/data/upper_vlm_survey/pylib")
import cv2
import numpy as np
from xemb import geom as G
from xemb import src_mbfranka as MF
from xemb import src_molmobot as MB

out = sys.argv[1]
os.makedirs(os.path.join(out, "img"), exist_ok=True)
jobs, meta = [], {}
for ei, e in enumerate(MF.episodes("/data/harvest/out/xemb_proto/src/mb_franka")):
    if len(meta) >= 30:
        break
    if not e.exo:
        continue
    cam = e.exo[ei % len(e.exo)]
    idx = list(range(0, e.n, 3))
    fr = MB.read_frames(e.video(cam), idx)
    W, H = e.wh(cam)
    K = e.K(cam, 0)
    E = e.E(cam, 0) @ e.T_world_base(0)  # base -> cam (base and camera fixed in this config)
    tcp = e.tcp[:, :3]
    Rt = np.array([G.quat_wxyz_to_mat(q) for q in e.tcp[:, 3:]])
    uv_gt = np.array([G.project(K, E, p)[0] for p in tcp])
    vid = os.path.join(out, "img", e.name)
    os.makedirs(vid, exist_ok=True)
    for k in idx:
        if k in fr:
            p = os.path.join(vid, f"f{k:04d}.jpg")
            cv2.imwrite(p, fr[k])
            jobs.append({"key": f"fr|{e.name}|{k}|", "src": "fr", "ep": 0, "k": k, "arm": "", "image": p})
    np.savez_compressed(os.path.join(out, f"{e.name}.npz"), tcp=tcp, R=Rt, uv_gt=uv_gt, E=E, K=K,
                        idx=np.array(sorted(fr)), W=W, H=H)
    meta[e.name] = {"cam": cam, "n": int(e.n), "frames": len(fr), "E_moves_check_deg": float(
        np.degrees(np.arccos(np.clip((np.trace((e.E(cam, e.n - 1) @ e.T_world_base(e.n - 1))[:3, :3] @ E[:3, :3].T) - 1) / 2,
                                     -1, 1))))}
with open(os.path.join(out, "jobs.jsonl"), "w") as f:
    for j in jobs:
        f.write(json.dumps(j) + "\n")
json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
print("episodes", len(meta), "jobs", len(jobs))
