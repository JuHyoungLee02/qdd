"""SAM 3.1 verification sample for point rows (user-log 164 rule 1): per source, N random obj_point / place_point rows;
the row's name is the text prompt; PASS when the point lies on (within 5 px of) a detected mask with score >= 0.3.
usage: sam_verify.py POINTS_ROOT OUT_JSON N SOURCE [SOURCE ...]   (uv python 3.12 + venv_sam3 site dir, 1 GPU)"""
import json, os, sys
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
import site
site.addsitedir("/data/harvest/venv_sam3/lib/python3.12/site-packages")
sys.path.insert(0, "/data/harvest/src/sam3")
import cv2
import numpy as np
from harvest.perception.seg import Sam31Image

root, outp, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
seg = Sam31Image(thr=0.3)
res = {}
for src in sys.argv[4:]:
    rows = [json.loads(l) for l in open(os.path.join(root, src, "records.jsonl"))]
    rows = [r for r in rows if r["qa_kind"] in ("obj_point", "place_point")]
    pick = [rows[i] for i in np.random.default_rng(0).permutation(len(rows))[:n]]
    ok, det, bad = 0, 0, []
    for r in pick:
        img = cv2.imread(r["images"][0])
        if img is None:
            continue
        H, W = img.shape[:2]
        p = json.loads(r["answer"])["point"]
        u, v = int(p[0] * W / 1000), int(p[1] * H / 1000)
        out, _ = seg.segment(img[:, :, ::-1], [r["name"]])
        m = np.zeros((H, W), bool)
        for s, mk in out[r["name"]]:
            if s >= 0.3:
                m |= mk.astype(bool)
        if m.any():
            det += 1
        m = cv2.dilate(m.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
        hit = bool(m[min(v, H - 1), min(u, W - 1)])
        ok += hit
        if not hit and len(bad) < 10:
            bad.append(r["id"])
    res[src] = {"n": len(pick), "name_detected": det, "point_on_mask": ok,
                "pass_rate": round(ok / max(1, len(pick)), 3), "fail_ids": bad}
    print(src, json.dumps(res[src]), flush=True)
json.dump(res, open(outp, "w"), indent=1)
