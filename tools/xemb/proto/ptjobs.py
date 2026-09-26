"""Build Molmo2-ER gripper-pointing jobs on CALIBRATED open data (route-2 detector accuracy + T1 hide-and-recover):
MolmoBot RBY1 head frames (GT = 10 gripper geometry points per arm) and BEHAVIOR head frames (GT = gripper link masks).
usage: ptjobs.py OUT   (pod, CPU)"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/data/upper_vlm_survey/pylib")
import cv2
import numpy as np
from xemb import src_molmobot as MB
from xemb import src_behavior as B

out = sys.argv[1]
os.makedirs(os.path.join(out, "img"), exist_ok=True)
jobs, gt = [], {}
# MolmoBot RBY1 (50 train packages): every 10th frame
for e in MB.episodes("/data/harvest/out/xemb_proto/src/mb_rby1"):
    idx = list(range(1, e.n, 10))
    fr = MB.read_frames(e.video("head_camera"), idx)
    for k in idx:
        if k not in fr:
            continue
        img = os.path.join(out, "img", f"mb_{e.name}_{k:04d}.jpg")
        cv2.imwrite(img, fr[k])
        for arm in ("left", "right"):
            key = f"mb|{e.name}|{k}|{arm}"
            gt[key] = {"pts": np.nan_to_num(e.pts(f"{arm}_gripper", "head_camera", k), nan=-1).round(1).tolist(),
                       "other": np.nan_to_num(e.pts(f"{'right' if arm == 'left' else 'left'}_gripper", "head_camera", k),
                                              nan=-1).round(1).tolist()}
            jobs.append({"key": key, "src": "mb", "ep": 0, "k": k, "arm": arm, "image": img})
# BEHAVIOR (downloaded 2025 episodes): every 150th head frame, gripper masks
root = "/data/harvest/out/xemb_proto/src/b1k"
os.makedirs(os.path.join(out, "mask"), exist_ok=True)
for dp in sorted(glob.glob(os.path.join(root, "videos", "task-*", "observation.images.depth.head", "*.mp4")))[::3]:
    ep = os.path.basename(dp)[len("episode_"):-4]
    task = os.path.basename(os.path.dirname(os.path.dirname(dp)))
    try:
        meta = json.load(open(os.path.join(root, "meta", "episodes", task, f"episode_{ep}.json")))
    except Exception:
        continue
    mapping = {int(k): v for k, v in B._load(meta["ins_id_mapping"]).items()}
    ids = B._load(meta[f"{B.HEAD_CAM}::unique_ins_ids"])
    import av
    c = av.open(os.path.join(root, "videos", task, "observation.images.rgb.head", f"episode_{ep}.mp4"))
    n = c.streams.video[0].frames
    c.close()
    idx = list(range(300, max(n, 301), 600))[:2]
    rgb = B.decode(os.path.join(root, "videos", task, "observation.images.rgb.head", f"episode_{ep}.mp4"), idx, "rgb")
    seg = B.decode(os.path.join(root, "videos", task, "observation.images.seg_instance_id.head", f"episode_{ep}.mp4"),
                   idx, "seg", ids)
    for k in idx:
        if k not in rgb or k not in seg:
            continue
        img = os.path.join(out, "img", f"b1k_{ep}_{k:05d}.jpg")
        cv2.imwrite(img, rgb[k])
        for arm in ("left", "right"):
            m = np.isin(seg[k], [i for i in ids if f"{arm}_gripper" in mapping.get(i, "")])
            mo = np.isin(seg[k], [i for i in ids if f"{'right' if arm == 'left' else 'left'}_gripper" in mapping.get(i, "")])
            mp = os.path.join(out, "mask", f"b1k_{ep}_{k:05d}_{arm}.npz")
            np.savez_compressed(mp, m=m, o=mo)
            key = f"b1k|{ep}|{k}|{arm}"
            gt[key] = {"mask": mp, "px": int(m.sum())}
            jobs.append({"key": key, "src": "b1k", "ep": 0, "k": k, "arm": arm, "image": img})
with open(os.path.join(out, "jobs.jsonl"), "w") as f:
    for j in jobs:
        f.write(json.dumps(j) + "\n")
json.dump(gt, open(os.path.join(out, "gt.json"), "w"))
print("jobs", len(jobs), "mb", sum(j["src"] == "mb" for j in jobs), "b1k", sum(j["src"] == "b1k" for j in jobs))
