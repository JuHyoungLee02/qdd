"""Frame sheet: head (top row) + right wrist (bottom row) for the given frame stems of an OursPolicy frames dir.

  python tools/pre_r7/sheet.py --dir FRAMES --stems t005.61_close,t006.21_lift --out sheet.jpg
"""
import argparse
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--stems", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=336)
    a = ap.parse_args()
    stems = a.stems.split(",")
    hw, hh, ww, wh = a.w, a.w * 376 // 672, a.w, a.w * 240 // 424
    sheet = Image.new("RGB", (hw * len(stems), hh + wh + 18), "white")
    d = ImageDraw.Draw(sheet)
    for i, s in enumerate(stems):
        h = Image.open(os.path.join(a.dir, s + "_cam_head.jpg")).resize((hw, hh))
        w = Image.open(os.path.join(a.dir, s + "_cam_wrist_right.jpg")).resize((ww, wh))
        sheet.paste(h, (i * hw, 18))
        sheet.paste(w, (i * hw, 18 + hh))
        d.text((i * hw + 4, 3), s, fill="black")
    sheet.save(a.out, quality=88)


if __name__ == "__main__":
    main()
