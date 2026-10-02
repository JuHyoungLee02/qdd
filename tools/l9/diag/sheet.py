"""L9 v2 diagnosis: contact sheet of episode frames (PIL). Each tile is labelled with its frame index.
usage: python tools/l9/diag/sheet.py <frames dir> <out.png> <first> <last> [step=1] [cols=4] [width=640]
       [--crop x0 y0 x1 y1]  (crop box in source pixels, e.g. only the wrist half)"""
import os
import sys

from PIL import Image, ImageDraw


def main():
    a = sys.argv[1:]
    crop = None
    if "--crop" in a:
        i = a.index("--crop")
        crop = tuple(int(v) for v in a[i + 1:i + 5])
        a = a[:i] + a[i + 5:]
    d, out, f0, f1 = a[0], a[1], int(a[2]), int(a[3])
    step = int(a[4]) if len(a) > 4 else 1
    cols = int(a[5]) if len(a) > 5 else 4
    width = int(a[6]) if len(a) > 6 else 640
    tiles = []
    for k in range(f0, f1 + 1, step):
        p = os.path.join(d, f"f{k:04d}.jpg")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB")
        if crop:
            im = im.crop(crop)
        im = im.resize((width, int(im.height * width / im.width)))
        ImageDraw.Draw(im).text((4, 4), str(k), fill=(255, 0, 255))
        tiles.append(im)
    if not tiles:
        print("no frames")
        return
    rows = (len(tiles) + cols - 1) // cols
    h = tiles[0].height
    g = Image.new("RGB", (cols * width, rows * h))
    for i, t in enumerate(tiles):
        g.paste(t, ((i % cols) * width, (i // cols) * h))
    g.save(out)
    print(out, len(tiles))


if __name__ == "__main__":
    main()
