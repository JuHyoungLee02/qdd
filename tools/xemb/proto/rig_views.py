"""Head-view consistency per episode (the T4 camera is one per dataset; the head may be posed differently in some
episodes): first-frame 64x36 grey thumbnails, distance to the dataset median thumbnail, plus the T4 per-frame
chamfer of the mask frames (t4r2) grouped by episode, to pick a view threshold.
usage: rig_views.py RAW_ROOT OUT_JSON"""
import json, os, sys
import av
import numpy as np

raw, outp = sys.argv[1:3]
info = json.load(open(os.path.join(raw, "meta", "info.json")))
eps = [json.loads(x) for x in open(os.path.join(raw, "meta", "episodes.jsonl"))]
th = {}
for e in eps:
    ep = int(e["episode_index"])
    p = os.path.join(raw, info["video_path"].format(episode_chunk=ep // info["chunks_size"],
                                                    video_key="observation.images.cam_head", episode_index=ep))
    if not os.path.exists(p):
        continue
    with av.open(p) as c:
        for fr in c.decode(video=0):
            g = np.asarray(fr.to_image().convert("L").resize((64, 36)), float)
            th[ep] = (g - g.mean()) / (g.std() + 1e-6)
            break
M = np.median(np.stack(list(th.values())), 0)
d = {ep: float(np.mean((t - M) ** 2)) for ep, t in th.items()}
v = np.array(list(d.values()))
print("episodes", len(d), "dist pct 10/50/90/95/99", np.percentile(v, [10, 50, 90, 95, 99]).round(3).tolist())
json.dump(d, open(outp, "w"))
