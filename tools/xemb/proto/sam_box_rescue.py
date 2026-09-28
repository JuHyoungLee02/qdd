"""SAM 3.1 with the name + the Grounding DINO box (the second detector): a rejected row is rescued only when BOTH agree,
i.e. the point lies in the DINO box and in the box-prompted SAM mask (score >= 0.3). Writes the decision and an eye-check
sheet of the rescued rows (point + box + mask outline). usage: sam_box_rescue.py BOXES_JSON OUT_JSON SHEET_PREFIX"""
import json, os, sys
sys.path.insert(0, "/data/harvest/code_open8_b057c5a")
import site
site.addsitedir("/data/harvest/venv_sam3/lib/python3.12/site-packages")
sys.path.insert(0, "/data/harvest/src/sam3")
import cv2
import numpy as np
import torch
from harvest.perception.seg import Sam31Image

rows = json.load(open(sys.argv[1]))
seg = Sam31Image(thr=0.3)
P = seg.proc
res, tiles = [], []
for r in rows:
    img = cv2.imread(r["images"][0])
    H, W = img.shape[:2]
    p = json.loads(r["answer"])["point"]
    u, v = int(p[0] * W / 1000), int(p[1] * H / 1000)
    ok, used = False, None
    for s, (x0, y0, x1, y1) in sorted(r["gdino_boxes"], reverse=True)[:2]:
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            st = P.set_image(torch.from_numpy(np.ascontiguousarray(img[:, :, ::-1])).permute(2, 0, 1))
            P.reset_all_prompts(st)
            st = P.set_text_prompt(r["name"], st)
            st = P.add_geometric_prompt([(x0 + x1) / 2 / W, (y0 + y1) / 2 / H, (x1 - x0) / W, (y1 - y0) / H], True, st)
            for sc, mk in zip(st["scores"].float().cpu().numpy(), st["masks"][:, 0].cpu().numpy()):
                mk = mk.astype(bool)
                if sc >= 0.3 and mk[min(v, H - 1), min(u, W - 1)]:
                    ok, used = True, (mk, (x0, y0, x1, y1))
                    break
        if ok:
            break
    res.append({"id": r["id"], "src": r["src"], "name": r["name"], "dino_box": bool(r["gdino_boxes"]), "rescued": ok})
    if ok and len(tiles) < 20:
        vis = img.copy()
        cnt, _ = cv2.findContours(used[0].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnt, -1, (0, 255, 0), 2)
        x0, y0, x1, y1 = (int(t) for t in used[1])
        cv2.rectangle(vis, (x0, y0), (x1, y1), (255, 0, 0), 2)
        cv2.drawMarker(vis, (u, v), (0, 0, 255), cv2.MARKER_CROSS, 20, 3)
        cv2.putText(vis, f"{r['name'][:34]} ({r['src']})", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        tiles.append(cv2.resize(vis, (480, int(480 * H / W))))
by = {}
for x in res:
    b = by.setdefault(x["src"], [0, 0, 0])
    b[0] += 1
    b[1] += x["dino_box"]
    b[2] += x["rescued"]
summ = {"rows": len(res), "dino_box_on_point": sum(x["dino_box"] for x in res), "rescued": sum(x["rescued"] for x in res),
        "by_source": {k: {"n": v[0], "dino": v[1], "rescued": v[2]} for k, v in by.items()}}
json.dump({"summary": summ, "rows": res}, open(sys.argv[2], "w"), indent=1)
for s in range(2):
    t = tiles[s * 10:(s + 1) * 10]
    if not t:
        break
    h = min(x.shape[0] for x in t)
    t = [x[:h] for x in t]
    while len(t) % 2:
        t.append(np.zeros_like(t[0]))
    cv2.imwrite(f"{sys.argv[3]}_{s}.png", np.vstack([np.hstack(t[j:j + 2]) for j in range(0, len(t), 2)]))
print(json.dumps(summ))
