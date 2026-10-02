"""L9 v2 diagnosis: crop + upscale an image region for frame inspection (laptop or pod, PIL).
usage: python tools/l9/diag/crop.py <in> <out> <cx 0-1000> <cy 0-1000> [half_w_px=90] [scale=4]
Several inputs: python tools/l9/diag/crop.py --grid <out> <cx> <cy> <half> <scale> <in1> <in2> ... (side by side)."""
import sys

from PIL import Image


def crop(path, cx, cy, half, scale):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    x, y = cx / 1000 * W, cy / 1000 * H
    box = (int(max(0, x - half)), int(max(0, y - half * 0.75)), int(min(W, x + half)), int(min(H, y + half * 0.75)))
    c = im.crop(box)
    return c.resize((c.width * scale, c.height * scale), Image.LANCZOS)


def main():
    a = sys.argv[1:]
    if a[0] == "--grid":
        out, cx, cy, half, scale = a[1], float(a[2]), float(a[3]), int(a[4]), int(a[5])
        ims = [crop(p, cx, cy, half, scale) for p in a[6:]]
        W = sum(i.width for i in ims) + 4 * (len(ims) - 1)
        g = Image.new("RGB", (W, max(i.height for i in ims)), (255, 0, 255))
        x = 0
        for i in ims:
            g.paste(i, (x, 0))
            x += i.width + 4
        g.save(out)
        return
    inp, out, cx, cy = a[0], a[1], float(a[2]), float(a[3])
    half = int(a[4]) if len(a) > 4 else 90
    scale = int(a[5]) if len(a) > 5 else 4
    crop(inp, cx, cy, half, scale).save(out)


if __name__ == "__main__":
    main()
