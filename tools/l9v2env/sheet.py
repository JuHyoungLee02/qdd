"""Contact sheet of smoke frames (pod or local): python sheet.py DIR OUT.jpg START N [glob]."""
import glob
import os
import sys

from PIL import Image, ImageDraw

d, out, start, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
pat = sys.argv[5] if len(sys.argv) > 5 else "*_head.png"
ps = sorted(glob.glob(os.path.join(d, pat)))[start:start + n]
W, H, cols = 448, 251, 3
rows = max(1, (len(ps) + cols - 1) // cols)
sheet = Image.new("RGB", (W * cols, (H + 16) * rows), "white")
dr = ImageDraw.Draw(sheet)
for i, p in enumerate(ps):
    im = Image.open(p).convert("RGB").resize((W, H))
    x, y = (i % cols) * W, (i // cols) * (H + 16)
    sheet.paste(im, (x, y + 16))
    dr.text((x + 3, y + 2), os.path.basename(p).replace("_head.png", "")[:70], fill="black")
sheet.save(out, quality=85)
print(len(ps), out)
