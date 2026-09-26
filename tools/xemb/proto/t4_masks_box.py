"""SAM 3.1 arm masks with the text prompt 'robot arm' PLUS one positive box per arm (boxes from t4_boxes.py, nominal
camera). Keeps the text-only mask too, for comparison. A detection counts if score >= THR and it overlaps a box.
usage: t4_masks_box.py OUT BOXES_JSON [BOXES_JSON ...]   (x3/7a2a: uv python 3.12 + venv_sam3 site dir)"""
import json, os, sys
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
import site
site.addsitedir("/data/harvest/venv_sam3/lib/python3.12/site-packages")
sys.path.insert(0, "/data/harvest/src/sam3")
import cv2
import numpy as np
import torch
from harvest.perception.seg import Sam31Image

THR = 0.3
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
seg = Sam31Image(thr=0.1)
P = seg.proc
index = []
for ip in sys.argv[2:]:
    for it in json.load(open(ip)):
        img = cv2.imread(it["img"])[:, :, ::-1]
        h, w = img.shape[:2]
        inbox = np.zeros((h, w), bool)
        for x0, y0, x1, y1 in it["boxes"]:
            inbox[int(y0):int(y1) + 1, int(x0):int(x1) + 1] = True
        m_text = np.zeros((h, w), bool)
        m_box = np.zeros((h, w), bool)
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            st = P.set_image(torch.from_numpy(np.ascontiguousarray(img)).permute(2, 0, 1))
            P.reset_all_prompts(st)
            st = P.set_text_prompt("robot arm", st)
            for s, mk in zip(st["scores"].float().cpu().numpy(), st["masks"][:, 0].cpu().numpy()):
                if s >= THR:
                    m_text |= mk.astype(bool)
            for x0, y0, x1, y1 in it["boxes"]:
                box = [(x0 + x1) / 2 / w, (y0 + y1) / 2 / h, (x1 - x0) / w, (y1 - y0) / h]
                P.reset_all_prompts(st)  # one box at a time (add_geometric_prompt appends)
                st = P.set_text_prompt("robot arm", st)
                st = P.add_geometric_prompt(box, True, st)
                for s, mk in zip(st["scores"].float().cpu().numpy(), st["masks"][:, 0].cpu().numpy()):
                    mk = mk.astype(bool)
                    if s >= THR and (mk & inbox).sum() > 0.5 * mk.sum():
                        m_box |= mk
        name = f"{it['tag']}_ep{it['ep']:06d}_f{it['k']:04d}.npz"
        np.savez_compressed(os.path.join(out, name), m=m_box, m_text=m_text)
        index.append(dict(it, mask=os.path.join(out, name), px=int(m_box.sum()), px_text=int(m_text.sum())))
json.dump(index, open(os.path.join(out, "index.json"), "w"))
for tag in sorted({i["tag"] for i in index}):
    t = [i for i in index if i["tag"] == tag]
    print(tag, len(t), "text>=200px", sum(i["px_text"] >= 200 for i in t), "box>=200px", sum(i["px"] >= 200 for i in t))
