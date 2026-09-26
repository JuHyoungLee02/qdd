"""Eye check of DROID C': tiles (exterior | wrist) of one episode's C' rows, labelled with step and gripper command.
usage: droid_sheet.py RECORDS_C OUT_JPG [EPISODE_NTH]"""
import json, sys
sys.path.append("/data/harvest/pylib_moge")
import cv2
import numpy as np

recs = [json.loads(l) for l in open(sys.argv[1])]
eps = sorted({r["id"].split("_")[1] for r in recs}, key=int)
ep = eps[int(sys.argv[3]) if len(sys.argv) > 3 else 0]
rows = [r for r in recs if r["id"].split("_")[1] == ep][:10]
tiles = []
for r in rows:
    a, b = (cv2.imread(p) for p in r["images"])
    t = np.hstack([a, b])
    c = json.loads(r["answer"])["command"]
    lab = f"{r['step']} t{r['t']} {c.get('gripper', '')} {c.get('position_m', '')}"
    cv2.putText(t, lab, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    tiles.append(t)
cv2.imwrite(sys.argv[2], np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(ep, rows[0]["prompt"].split("TASK: ")[1].split("\n")[0], len(tiles))
