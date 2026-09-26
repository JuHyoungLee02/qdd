"""SAM 3.1 'robot arm' masks for frames listed in index json files (T4 on more rigs).
usage: t4_masks_idx.py OUT INDEX_JSON [INDEX_JSON ...]   (x3: uv python 3.12 + venv_sam3 site dir)"""
import json, os, sys
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
import site
site.addsitedir("/data/harvest/venv_sam3/lib/python3.12/site-packages")
sys.path.insert(0, "/data/harvest/src/sam3")
import cv2
import numpy as np
from harvest.perception.seg import Sam31Image

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
seg = Sam31Image(thr=0.3)
index = []
for ip in sys.argv[2:]:
    for it in json.load(open(ip)):
        img = cv2.imread(it["img"])[:, :, ::-1]
        res, _ = seg.segment(img, ["robot arm"])
        m = np.zeros(img.shape[:2], bool)
        for s, mk in res["robot arm"]:
            if s >= 0.3:
                m |= mk.astype(bool)
        name = f"{it['tag']}_ep{it['ep']:06d}_f{it['k']:04d}.npz"
        np.savez_compressed(os.path.join(out, name), m=m)
        index.append(dict(it, mask=os.path.join(out, name), px=int(m.sum())))
json.dump(index, open(os.path.join(out, "index.json"), "w"))
print("masks", len(index))
