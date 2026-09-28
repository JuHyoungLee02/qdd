"""Point rows -> SAM-verified rows (user-log 165: data that may lower accuracy is not used). Every obj_point /
place_point row is kept only if SAM 3.1, prompted with the row's name, finds a mask (score >= 0.3) under the point
(5 px tolerance). ee_point rows are kept as converted (their gates are geometric: GT gripper mask / T4 <= 5 px).
Images are encoded once per file (rows sharing an image share the SAM image pass).
usage: sam_filter.py POINTS_ROOT SOURCE [SOURCE ...]   -> <root>/<source>/records_verified.jsonl + verify.json"""
import json, os, sys
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
import site
site.addsitedir("/data/harvest/venv_sam3/lib/python3.12/site-packages")
sys.path.insert(0, "/data/harvest/src/sam3")
import cv2
import numpy as np
from harvest.perception.seg import Sam31Image

root = sys.argv[1]
seg = Sam31Image(thr=0.3)
for src in sys.argv[2:]:
    rows = [json.loads(l) for l in open(os.path.join(root, src, "records.jsonl"))]
    by_img = {}
    for r in rows:
        if r["qa_kind"] != "ee_point":
            by_img.setdefault(r["images"][0], []).append(r)
    keep = [r for r in rows if r["qa_kind"] == "ee_point"]
    st = {"obj_place_in": 0, "detected": 0, "kept": 0}
    for img_p, rs in by_img.items():
        img = cv2.imread(img_p)
        if img is None:
            continue
        H, W = img.shape[:2]
        names = sorted({r["name"] for r in rs})
        out, _ = seg.segment(img[:, :, ::-1], names, cache_text=False)
        masks = {}
        for nm in names:
            m = np.zeros((H, W), bool)
            for s, mk in out[nm]:
                if s >= 0.3:
                    m |= mk.astype(bool)
            masks[nm] = cv2.dilate(m.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
        for r in rs:
            st["obj_place_in"] += 1
            m = masks[r["name"]]
            st["detected"] += bool(m.any())
            p = json.loads(r["answer"])["point"]
            u, v = min(int(p[0] * W / 1000), W - 1), min(int(p[1] * H / 1000), H - 1)
            if m[v, u]:
                keep.append(dict(r, sam_verified=True))
                st["kept"] += 1
    with open(os.path.join(root, src, "records_verified.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in keep)
    st["ee_kept"] = sum(r["qa_kind"] == "ee_point" for r in keep)
    st["obj_place_pass_rate"] = round(st["kept"] / max(1, st["obj_place_in"]), 3)
    json.dump(st, open(os.path.join(root, src, "verify.json"), "w"), indent=1)
    print(src, json.dumps(st), flush=True)
