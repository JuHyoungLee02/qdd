"""Second detector for SAM-rejected point rows (user-log 171 (2)): Grounding DINO base (/data/harvest/models/gdino-base,
Apache-2.0) with the row's name; keep the boxes (score >= 0.35) that contain the labelled point.
usage (venv_train, 1 GPU): gdino_boxes.py REJECTED_JSONL N OUT_JSON"""
import json, sys
sys.path.insert(0, "/data/harvest/pylib_moge")
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

M = "/data/harvest/models/gdino-base"
proc = AutoProcessor.from_pretrained(M)
model = AutoModelForZeroShotObjectDetection.from_pretrained(M).cuda().eval()
rows = [json.loads(l) for l in open(sys.argv[1])]
by = {}
for r in rows:
    by.setdefault(r["src"], []).append(r)
n = int(sys.argv[2])
rng = np.random.default_rng(0)
pick = []
for s, rs in sorted(by.items()):  # stratified over sources
    k = max(1, round(n * len(rs) / len(rows)))
    pick += [rs[i] for i in rng.permutation(len(rs))[:k]]
pick = pick[:n]
out = []
for r in pick:
    img = Image.open(r["images"][0]).convert("RGB")
    W, H = img.size
    p = json.loads(r["answer"])["point"]
    u, v = p[0] * W / 1000, p[1] * H / 1000
    inp = proc(images=img, text=r["name"].lower().strip() + ".", return_tensors="pt").to("cuda")
    with torch.inference_mode():
        o = model(**inp)
    det = proc.post_process_grounded_object_detection(o, inp.input_ids, threshold=0.35, text_threshold=0.25,
                                                      target_sizes=[(H, W)])[0]
    boxes = [(float(s), [float(x) for x in b]) for s, b in zip(det["scores"], det["boxes"])
             if b[0] <= u <= b[2] and b[1] <= v <= b[3]]
    out.append(dict(r, gdino_boxes=boxes, W=W, H=H))
json.dump(out, open(sys.argv[3], "w"))
print("rows", len(out), "with a box on the point", sum(bool(r["gdino_boxes"]) for r in out))
