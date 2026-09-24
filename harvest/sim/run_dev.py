"""Pod runner for T11/T12 (Isaac only). DEV seeds 0-29 only; TEST/TEST-P5 seeds are refused.

  python.sh -m harvest.sim.run_dev boot  --out DIR                 # seed 0: 100 steps, settle, RTF, cam_head PNG
  python.sh -m harvest.sim.run_dev dev   --out DIR --kind P0 [--seeds 0-29] [--frames]
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

DEV_SEEDS = range(0, 30)


def _seeds(s: str):
    a, _, b = s.partition("-")
    out = list(range(int(a), int(b or a) + 1))
    bad = [x for x in out if x not in DEV_SEEDS]
    if bad:
        raise SystemExit(f"refused: seeds {bad} are not DEV (0-29)")
    return out


def _save_png(img: np.ndarray, path: str, max_kb=300):
    from PIL import Image
    im = Image.fromarray(img)
    im.save(path, optimize=True)
    if os.path.getsize(path) > max_kb * 1024:
        im.quantize(colors=128).save(path, optimize=True)
    return os.path.getsize(path)


def _depth_vis(d: np.ndarray) -> np.ndarray:
    d = np.nan_to_num(d, nan=0.0, posinf=0.0)
    v = d[d > 0]
    lo, hi = (np.percentile(v, 1), np.percentile(v, 99)) if v.size else (0, 1)
    x = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
    x = (255 * (1 - x)).astype(np.uint8)
    x[d <= 0] = 0
    return np.stack([x, x, x], -1)


def boot(out: str):
    from .scene import OBJ_GEOM, make_env
    t0 = time.perf_counter()
    env = make_env(0, headless=True, cameras=("cam_head",), depth=True)
    t_make = time.perf_counter() - t0
    env.reset(settle_s=0.0)  # one reset write, no settling: the 100 steps below are the settle check
    spawn = {k: env.object_pose(k)[0].copy() for k in env.present}
    q = env.robot.data.joint_pos[0, env.arm_ids].cpu().numpy()
    from .scene import GRIP_MAX_W
    hold = np.concatenate([q, [GRIP_MAX_W]])
    speeds = {k: [] for k in env.present}
    tw = time.perf_counter()
    for i in range(100):
        env.step(hold)
        for k in env.present:
            speeds[k].append(env.object_vel(k))
    wall = time.perf_counter() - tw
    rgb = env.camera_rgb("cam_head")
    dep = env.camera_depth("cam_head")
    res = {"seed": 0, "steps": 100, "sim_s": round(env.sim_time, 3), "wall_s": round(wall, 2),
           "rtf_cam_head": round(env.sim_time / wall, 3), "make_env_s": round(t_make, 1),
           "tcp_offset_m": round(env.tcp_offset, 4), "tip_offset_m": round(env.tip_offset, 4),
           "layout": {k: [round(v, 4) for v in p] for k, p in env.layout.items()}, "objects": {}}
    for k in env.present:
        p, qq = env.object_pose(k)
        res["objects"][k] = {
            "final_speed_mm_s": round(speeds[k][-1] * 1e3, 3),
            "max_speed_last_10_mm_s": round(max(speeds[k][-10:]) * 1e3, 3),
            "settle_disp_mm": round(float(np.linalg.norm(p - spawn[k])) * 1e3, 2),
            "bottom_z_table_mm": round((p[2] - OBJ_GEOM[k]["half_extents"][2] - env.table_top_z) * 1e3, 2)}
    res["settled_lt_1mm_s"] = all(v["max_speed_last_10_mm_s"] < 1.0 for v in res["objects"].values())
    res["img_shape"] = list(rgb.shape)
    res["depth_valid_frac"] = round(float(np.isfinite(dep).mean()), 3)
    res["depth_range_m"] = [round(float(np.nanmin(dep)), 3), round(float(np.nanmax(dep[np.isfinite(dep)])), 3)]
    os.makedirs(out, exist_ok=True)
    res["png_bytes"] = _save_png(rgb, f"{out}/scene_seed0.png")
    _save_png(_depth_vis(dep), f"{out}/scene_seed0_depth.png")
    # head camera intrinsics as used
    cam = env.scene["cam_head"]
    res["cam_head_K"] = np.round(cam.data.intrinsic_matrices[0].cpu().numpy(), 2).tolist()
    res["cam_head_pos_w"] = np.round(cam.data.pos_w[0].cpu().numpy(), 4).tolist()
    print("BOOT_RESULT " + json.dumps(res), flush=True)
    with open(f"{out}/boot_seed0.json", "w") as f:
        json.dump(res, f, indent=1)


def dev(out: str, kind: str, seeds, frames: bool):
    from .planner import run_episode
    from .scene import make_env
    os.makedirs(out, exist_ok=True)
    cams = ("cam_head",) if frames else ()
    env = None
    path = f"{out}/dev_{kind}.jsonl"
    for s in seeds:
        if env is None:
            env = make_env(s, headless=True, cameras=cams, depth=False)
        else:
            env.set_seed(s)
        shots = []

        def on_step(e, pl, _last=[None]):
            if frames and pl.phase != _last[0]:
                _last[0] = pl.phase
                shots.append((pl.phase, e.camera_rgb("cam_head")))

        r = run_episode(env, kind=kind, seed=s, on_step=on_step if frames else None)
        pl = r.pop("planner")
        r["decision_points_head"] = [(round(t, 2), d, a) for t, d, a in __import__(
            "harvest.sim.planner", fromlist=["decision_points"]).decision_points(pl)[:3]]
        print("EP " + json.dumps(r), flush=True)
        with open(path, "a") as f:
            f.write(json.dumps(r) + "\n")
        if frames and shots:
            from PIL import Image, ImageDraw
            w, h = 336, 188
            n = len(shots)
            sheet = Image.new("RGB", (w * min(n, 4), h * ((n + 3) // 4)))
            for i, (ph, img) in enumerate(shots):
                im = Image.fromarray(img).resize((w, h))
                ImageDraw.Draw(im).text((5, 5), ph, fill=(255, 255, 0))
                sheet.paste(im, ((i % 4) * w, (i // 4) * h))
            sheet.save(f"{out}/frames_{kind}_s{s}.png", optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["boot", "dev"])
    ap.add_argument("--out", default="/data/juhyoung_qdd/out/t11_12")
    ap.add_argument("--kind", default="P0", choices=["P0", "P1", "P2"])
    ap.add_argument("--seeds", default="0-29")
    ap.add_argument("--frames", action="store_true")
    a = ap.parse_args()
    if a.mode == "boot":
        boot(a.out)
    else:
        dev(a.out, a.kind, _seeds(a.seeds), a.frames)
    os._exit(0)  # SimulationApp.close() hangs in this chroot; results are already flushed


if __name__ == "__main__":
    main()
