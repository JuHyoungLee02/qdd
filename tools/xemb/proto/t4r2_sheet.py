"""Contact sheet: box-prompted (green) vs text-only (red) arm masks + nominal boxes (blue). usage: t4r2_sheet.py INDEX TAG OUT_JPG"""
import json, sys
sys.path.append("/data/harvest/pylib_moge")
import cv2
import numpy as np

idx = [i for i in json.load(open(sys.argv[1])) if i["tag"] == sys.argv[2] and i["boxes"]]
pick = [idx[j] for j in np.random.default_rng(3).permutation(len(idx))[:8]]
tiles = []
for it in pick:
    img = cv2.imread(it["img"])
    z = np.load(it["mask"])
    ov = img.copy()
    ov[z["m"]] = (0.5 * ov[z["m"]] + [0, 127, 0]).astype(np.uint8)
    ov[z["m_text"]] = (0.6 * ov[z["m_text"]] + [0, 0, 100]).astype(np.uint8)
    for x0, y0, x1, y1 in it["boxes"]:
        cv2.rectangle(ov, (int(x0), int(y0)), (int(x1), int(y1)), (255, 0, 0), 2)
    tiles.append(cv2.resize(ov, (448, 251)))
rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
cv2.imwrite(sys.argv[3], np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
print(len(tiles))
