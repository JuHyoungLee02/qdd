"""T4 step 1 (GPU, venv_sam3): SAM 3.1 text masks of the robot arms / grippers on RB2 head frames.
usage: t4_masks.py OUT N_EPS FRAMES_PER_EP"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
import site
site.addsitedir("/data/harvest/venv_sam3/lib/python3.12/site-packages")  # runs the .pth files (editable sam3)
sys.path.insert(0, "/data/harvest/src/sam3")
import cv2
import numpy as np
from harvest.perception.seg import Sam31Image

out, n_eps, per = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
os.makedirs(out, exist_ok=True)
root = "/data/harvest/data/marr_real/frames/RB2"
eps = sorted(glob.glob(os.path.join(root, "ep*")))
rng = np.random.default_rng(0)
eps = [eps[i] for i in sorted(rng.permutation(len(eps))[:n_eps])]
seg = Sam31Image(thr=0.3)
PH = ["robot arm", "robot gripper"]
index = []
for d in eps:
    fs = sorted(glob.glob(os.path.join(d, "f*.jpg")))
    if len(fs) < 10:
        continue
    for f in [fs[int(x)] for x in np.linspace(len(fs) * 0.2, len(fs) * 0.8, per).round()]:
        img = cv2.imread(f)[:, :, ::-1]
        res, _ = seg.segment(img, PH)
        m = np.zeros(img.shape[:2], bool)
        best = {}
        for ph in PH:
            for s, mk in res[ph]:
                if s >= 0.3:
                    m |= mk.astype(bool)
            best[ph] = res[ph][0][0] if res[ph] else 0.0
        ep = int(os.path.basename(d)[2:])
        k = int(os.path.basename(f)[1:5])
        per_ph = {ph: np.any([mk.astype(bool) for s, mk in res[ph] if s >= 0.3] or [np.zeros(img.shape[:2], bool)], axis=0) for ph in PH}
        np.savez_compressed(os.path.join(out, f"ep{ep:06d}_f{k:04d}.npz"), m=m, arm=per_ph["robot arm"], grip=per_ph["robot gripper"])
        index.append({"ep": ep, "k": k, "img": f, "px": int(m.sum()), "best": best})
json.dump(index, open(os.path.join(out, "index.json"), "w"))
print("masks", len(index))
