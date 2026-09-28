"""AgiBot TCP offset probe: on Pick-end frames, draw end_pos + d * (end orientation axis k) for k in x/y/z (both
quaternion orders xyzw / wxyz) and d in 0.05..0.25 m, to see which axis / length reaches the fingertip centre.
usage: agb_tcp.py KEEP META TASK OUT_JPG"""
import json, os, sys, glob
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
import cv2
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from xemb.agb_projtest import load_cam, proj, frames

keep, meta, task, outp = sys.argv[1:5]
info = {e["episode_id"]: e for e in json.load(open(os.path.join(meta, "task_info", f"task_{task}.json")))}
tiles = []
COL = {0: (0, 0, 255), 1: (0, 255, 0), 2: (255, 0, 0)}
for npz in sorted(glob.glob(os.path.join(keep, "npz", task, "*.npz")))[:4]:
    ep = int(os.path.basename(npz)[:-4])
    z = np.load(npz)
    K, dist, Ts = load_cam(os.path.join(keep, "params", task, str(ep), "parameters", "camera"))
    k = [s["end_frame"] for s in info[ep]["label_info"]["action_config"] if "pick" in s["skill"].lower()][0]
    fr = frames(os.path.join(keep, "obs", task, str(ep), "videos", "head_color.mp4"), [k])
    for order in ("xyzw", "wxyz"):
        img = fr[k].copy()
        E = np.linalg.inv(Ts[k])
        for arm in (1,):
            p, q = z["end_pos"][k][arm], z["end_quat"][k][arm]
            q = q if order == "xyzw" else np.r_[q[1:], q[0]]
            R = Rot.from_quat(q).as_matrix()
            for ax in range(3):
                for d in (0.05, 0.10, 0.15, 0.20, 0.25):
                    uv = proj(K, dist, E, (p + d * R[:, ax])[None])
                    if uv is not None:
                        cv2.circle(img, (int(uv[0, 0]), int(uv[0, 1])), 3 + int(d * 20), COL[ax], 1)
        cv2.putText(img, f"{ep} f{k} {order} x=red y=green z=blue", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        tiles.append(img)
h = min(t.shape[0] for t in tiles)
cv2.imwrite(outp, np.vstack([np.hstack(tiles[j:j + 2]) for j in range(0, len(tiles) - 1, 2)]))
