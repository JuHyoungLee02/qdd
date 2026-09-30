"""L9 frame-review contact sheets (pod or laptop): for N random episodes of a collect root, one row per episode =
head f0 | wrist f0 | head middle call | wrist middle call | head last call, captioned with family / task / arm /
success. usage: python tools/l9/sheet.py <collect root> <out.png> [--n 12] [--seed 0] [--family F] [--success]"""
import glob
import json
import os
import random
import sys

from PIL import Image, ImageDraw

W, H = 336, 188


def calls(d):
    return sorted(glob.glob(os.path.join(d, "calls", "c*")))


def tile(p, w=W, h=H):
    if p and os.path.exists(p):
        return Image.open(p).convert("RGB").resize((w, h))
    return Image.new("RGB", (w, h), (40, 40, 40))


def main():
    root, out = sys.argv[1], sys.argv[2]
    arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d  # noqa: E731
    metas = [m for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True)]
    rows = []
    for m in metas:
        meta = json.load(open(m))
        if meta.get("gen") != "l9":
            continue
        if arg("--family", "") and meta.get("env_family") != arg("--family", ""):
            continue
        if "--success" in sys.argv and not meta.get("success"):
            continue
        rows.append((os.path.dirname(m), meta))
    random.Random(arg("--seed", 0)).shuffle(rows)
    rows = rows[: arg("--n", 12)]
    sheet = Image.new("RGB", (5 * W, len(rows) * (H + 16)), (0, 0, 0))
    dr = ImageDraw.Draw(sheet)
    for i, (d, meta) in enumerate(rows):
        cs = calls(d)
        if not cs:
            continue
        mid, last = cs[len(cs) // 2], cs[-1]
        ims = [os.path.join(cs[0], "img1_head_camera.png"), os.path.join(cs[0], "img2_right_wrist_camera.png"),
               os.path.join(mid, "img1_head_camera.png"), os.path.join(mid, "img2_right_wrist_camera.png"),
               os.path.join(last, "img1_head_camera.png")]
        y = i * (H + 16)
        for j, p in enumerate(ims):
            sheet.paste(tile(p), (j * W, y + 16))
        dr.text((4, y + 2), f"{meta.get('layout')} | {meta.get('task_id')} | {meta.get('arm')} | ok={meta.get('success')} "
                            f"| {meta.get('light_family')} | {meta.get('instruction', '')[:90]}", fill=(255, 255, 0))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sheet.save(out)
    print(json.dumps({"rows": len(rows), "out": out}))


if __name__ == "__main__":
    main()
