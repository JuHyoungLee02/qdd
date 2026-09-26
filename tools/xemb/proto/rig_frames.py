"""Sample head frames of ROBOTIS LeRobot datasets for T4 on more rigs. usage: rig_frames.py RAW_ROOT TAG OUT N_EPS PER_EP"""
import json, os, sys
import av
import numpy as np

raw, tag, out, n_eps, per = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
info = json.load(open(os.path.join(raw, "meta", "info.json")))
eps = [json.loads(l) for l in open(os.path.join(raw, "meta", "episodes.jsonl"))]
rng = np.random.default_rng(0)
pick = sorted(rng.permutation(len(eps))[:n_eps].tolist())
os.makedirs(out, exist_ok=True)
index = []
for i in pick:
    e = eps[i]
    ep, n = int(e["episode_index"]), int(e["length"])
    c = ep // info["chunks_size"]
    vp = os.path.join(raw, info["video_path"].format(episode_chunk=c, video_key="observation.images.cam_head", episode_index=ep))
    if not os.path.exists(vp):
        continue
    ks = sorted({int(x) for x in np.linspace(n * 0.15, n * 0.85, per).round()})
    want = set(ks)
    d = os.path.join(out, f"{tag}_ep{ep:06d}")
    os.makedirs(d, exist_ok=True)
    with av.open(vp) as cont:
        for k, fr in enumerate(cont.decode(video=0)):
            if k in want:
                p = os.path.join(d, f"f{k:04d}.jpg")
                fr.to_image().save(p, quality=90)
                index.append({"tag": tag, "ep": ep, "k": k, "img": p, "task": (e.get("tasks") or [""])[0]})
                want.discard(k)
            if not want:
                break
json.dump(index, open(os.path.join(out, f"{tag}_frames.json"), "w"))
print(tag, "episodes", len(pick), "frames", len(index))
