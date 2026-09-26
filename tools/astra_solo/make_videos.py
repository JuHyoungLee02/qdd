"""Videos of saved Astra-solo episodes (no model calls, originals untouched):
- <run>/<variant>_s<seed>.mp4: the sparse head | right-wrist jpgs in <episode>/frames/ (every 5th control tick at
  20 Hz = 4 fps sim time) played at 4 fps = real time, H.264;
- <run>/<variant>_s<seed>_astra.mp4: per call site, the two PNGs Astra received (head with overlay | right wrist) with
  the parsed answer (mode, target, gripper, status, evidence, reason) and the measured result under them, 2 s per call;
- <videos root>/index.json and index.md: result, calls, KRW, motion seconds, video paths, frame counts, sizes.
ffmpeg = the libx264 build bundled with imageio_ffmpeg in the Isaac rootfs (pod), run as a plain binary.
usage: python make_videos.py <videos root> <run name>=<episode root> [...]"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw

FFMPEG = ("/data/juhyoung_infra/rootfs/cyclo-lab-2.0.0/isaac-sim/kit/python/lib/python3.11/site-packages/"
          "imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2")
FRAMES_FPS = 4  # VIDEO_EVERY 5 ticks at 20 Hz
CALL_S = 2


def ffmpeg(pattern: str, fps: float, out: str) -> None:
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", pattern, "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-r", str(max(fps, 4)), out],
                   check=True)


def astra_view(ep: str, res: dict, tmp: str) -> int:
    hist = {int(h.split(":")[0]): h for h in res.get("history", []) if h.split(":")[0].isdigit()}
    n = 0
    for c in res["calls"]:
        if c["attempt"] != 0:
            continue
        d = os.path.join(ep, "calls", f"c{c['call']:03d}")
        hp, wp = os.path.join(d, "img1_head_camera.png"), os.path.join(d, "img2_right_wrist_camera.png")
        if not (os.path.exists(hp) and os.path.exists(wp)):
            continue
        h = Image.open(hp).convert("RGB")
        w = Image.open(wp).convert("RGB")
        w = w.resize((int(w.width * h.height / w.height), h.height))
        p = c.get("parsed") or {}
        cmd, a = p.get("command") or {"mode": "invalid"}, p.get("assessment") or {}
        lines = [f"{res['variant']} s{res['seed']} {res.get('model')}  call site {c['site']}  "
                 f"latency {c['latency_s']:.1f} s  {c['cost_usd'] * 1450:.1f} KRW",
                 "COMMAND " + json.dumps(cmd), f"status {a.get('execution_status')}  confidence {a.get('confidence')}  "
                 f"view {a.get('evidence_view')}"]
        lines += textwrap.wrap("evidence: " + str(a.get("evidence", "")), 150)
        lines += textwrap.wrap("reason: " + str(p.get("reason", "")), 150)
        lines += textwrap.wrap("result: " + hist.get(c["site"], "").split(": ", 1)[-1], 150)
        if not c["valid"]:
            lines += textwrap.wrap("INVALID: " + "; ".join(c["errors"]), 150)
        th = 16 * len(lines) + 10
        im = Image.new("RGB", (h.width + w.width, h.height + th), (0, 0, 0))
        im.paste(h, (0, 0))
        im.paste(w, (h.width, 0))
        dr = ImageDraw.Draw(im)
        if cmd.get("point_2d"):  # E-PT point command: the pointed spot in the head image (cyan cross + ring)
            px, py = cmd["point_2d"][0] / 1000 * h.width, cmd["point_2d"][1] / 1000 * h.height
            dr.ellipse([px - 9, py - 9, px + 9, py + 9], outline=(0, 255, 255), width=2)
            dr.line([px - 14, py, px + 14, py], fill=(0, 255, 255), width=1)
            dr.line([px, py - 14, px, py + 14], fill=(0, 255, 255), width=1)
        for i, t in enumerate(lines):
            dr.text((6, h.height + 5 + 16 * i), t, fill=(255, 255, 0) if i == 1 else (255, 255, 255))
        W, H = 1400, 600  # fixed canvas so every call frame has the same size
        can = Image.new("RGB", (W, H), (0, 0, 0))
        im.thumbnail((W, H))
        can.paste(im, (0, 0))
        can.save(os.path.join(tmp, f"a{n:04d}.png"))
        n += 1
    return n


def main():
    root = sys.argv[1]
    rows = []
    for spec in sys.argv[2:]:
        run, src = spec.split("=", 1)
        od = os.path.join(root, run)
        os.makedirs(od, exist_ok=True)
        for rp in sorted(glob.glob(os.path.join(src, "*", "*", "s*", "result.json"))):
            ep = os.path.dirname(rp)
            res = json.load(open(rp))
            vdir = os.path.basename(os.path.dirname(ep))  # E-PT OOD-H: standard_tz0.82 (else = the variant)
            name = f"{vdir if vdir.startswith(res['variant'] + '_tz') else res['variant']}_s{res['seed']}"
            row = {"run": run, "episode": ep, "variant": res["variant"], "seed": res["seed"], "model": res.get("model"),
                   "success": res["success"], "end_reason": res["end_reason"], "n_calls": res["n_calls"],
                   "cost_krw": res.get("cost_krw"), "motion_s": res.get("sim_t"), "t_success": res.get("t_success"),
                   "wall_s": res.get("wall_s")}
            fr = sorted(glob.glob(os.path.join(ep, "frames", "f*.jpg")))
            if fr:
                out = os.path.join(od, name + ".mp4")
                ffmpeg(os.path.join(ep, "frames", "f%04d.jpg"), FRAMES_FPS, out)
                row.update(video=out, video_frames=len(fr), video_fps=FRAMES_FPS, video_s=len(fr) / FRAMES_FPS,
                           video_bytes=os.path.getsize(out))
            tmp = os.path.join(od, "_tmp_" + name)
            os.makedirs(tmp, exist_ok=True)
            n = astra_view(ep, res, tmp)
            if n:
                out = os.path.join(od, name + "_astra.mp4")
                ffmpeg(os.path.join(tmp, "a%04d.png"), 1.0 / CALL_S, out)
                row.update(astra_video=out, astra_calls=n, astra_bytes=os.path.getsize(out))
            shutil.rmtree(tmp)
            rows.append(row)
            print(json.dumps(row), flush=True)
    with open(os.path.join(root, "index.json"), "w") as f:
        json.dump(rows, f, indent=1)
    md = ["# Astra-solo episode videos", "", "| run | episode | model | success | calls | KRW | motion s | video (fps, frames, MB) "
          "| Astra view (calls, MB) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        v = f"{os.path.basename(r['video'])} ({r['video_fps']}, {r['video_frames']}, {r['video_bytes'] / 1e6:.2f})" \
            if r.get("video") else "—"
        a = f"{os.path.basename(r['astra_video'])} ({r['astra_calls']}, {r['astra_bytes'] / 1e6:.2f})" \
            if r.get("astra_video") else "—"
        md.append(f"| {r['run']} | {r['variant']} s{r['seed']} | {r['model']} | {int(r['success'])} | {r['n_calls']} | "
                  f"{r['cost_krw']} | {r['motion_s']} | {v} | {a} |")
    open(os.path.join(root, "index.md"), "w").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()
