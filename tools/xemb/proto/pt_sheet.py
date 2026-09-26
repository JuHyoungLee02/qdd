"""Eye check of point records: draw the answer point on 8 random images. usage: pt_sheet.py RECORDS_P OUT_JPG"""
import json, sys
sys.path.append("/data/harvest/pylib_moge")
import cv2
import numpy as np

rs = [json.loads(l) for l in open(sys.argv[1])]
tiles = []
for i in np.random.default_rng(5).permutation(len(rs))[:8]:
    r = rs[i]
    im = cv2.imread(r["images"][0])
    u, v = json.loads(r["answer"])["point"]
    cv2.circle(im, (u, v), 6, (0, 0, 255), 2)
    cv2.putText(im, r["id"][-22:], (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    tiles.append(cv2.resize(im, (448, 251)))
cv2.imwrite(sys.argv[2], np.vstack([np.hstack(tiles[j:j + 2]) for j in range(0, 8, 2)]), [cv2.IMWRITE_JPEG_QUALITY, 80])
print(rs[0]["prompt"][:900])
