"""Pod runner for T11/T12 (Isaac only). DEV seeds 0-29 only; TEST/TEST-P5 seeds are refused.

  python.sh -m harvest.sim.run_dev boot  --out DIR [--cams cam_head,cam_wrist_right]  # seed 0: settle, RTF, PNGs
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


SHORT = {"cam_head": "head", "cam_wrist_right": "wrist", "cam_wrist_left": "wrist_left"}


def boot(out: str, cams, tag: str = "v2", sim_device: str = "cpu"):
    from .scene import GRIP_MAX_W, OBJ_GEOM, make_env
    t0 = time.perf_counter()
    env = make_env(0, headless=True, cameras=cams, depth=True, sim_device=sim_device)
    t_make = time.perf_counter() - t0
    env.reset(settle_s=0.0)  # one reset write, no settling: the 100 steps below are the settle check
    spawn = {k: env.object_pose(k)[0].copy() for k in env.present}
    q = env.robot.data.joint_pos[0, env.arm_ids].cpu().numpy()
    hold = np.concatenate([q, [GRIP_MAX_W]])
    speeds = {k: [] for k in env.present}
    tw = time.perf_counter()
    for i in range(100):
        env.step(hold)
        for k in env.present:
            speeds[k].append(env.object_vel(k))
    wall = time.perf_counter() - tw
    r = env.robot
    jn = r.joint_names
    jp = r.data.joint_pos[0].cpu().numpy()
    res = {"seed": 0, "steps": 100, "cameras": list(cams), "sim_device": env.sim_device, "sim_s": round(env.sim_time, 3), "wall_s": round(wall, 2),
           "rtf": round(env.sim_time / wall, 3), "make_env_s": round(t_make, 1),
           "is_fixed_base": bool(r.is_fixed_base), "num_joints": len(jn),
           "joints": {n: round(float(jp[jn.index(n)]), 4) for n in ("lift_joint", "head_joint1", "head_joint2",
                                                                   "arm_r_joint1", "arm_r_joint2", "arm_r_joint4",
                                                                   "gripper_r_joint1", "gripper_r_joint2")},
           "root_pos_w": np.round(r.data.root_pos_w[0].cpu().numpy(), 4).tolist(),
           "tcp_offset_m": round(env.tcp_offset, 4), "tip_offset_m": round(env.tip_offset, 4),
           "layout": {k: [round(v, 4) for v in p] for k, p in env.layout.items()}, "objects": {}, "cams": {}}
    for k in env.present:
        p, qq = env.object_pose(k)
        res["objects"][k] = {
            "final_speed_mm_s": round(speeds[k][-1] * 1e3, 3),
            "max_speed_last_10_mm_s": round(max(speeds[k][-10:]) * 1e3, 3),
            "settle_disp_mm": round(float(np.linalg.norm(p - spawn[k])) * 1e3, 2),
            "bottom_z_table_mm": round((p[2] - OBJ_GEOM[k]["half_extents"][2] - env.table_top_z) * 1e3, 2)}
    res["settled_lt_1mm_s"] = all(v["max_speed_last_10_mm_s"] < 1.0 for v in res["objects"].values())
    os.makedirs(out, exist_ok=True)
    for c in cams:
        rgb, dep = env.camera_rgb(c), env.camera_depth(c)
        cam = env.scene[c]
        fin = dep[np.isfinite(dep)]
        res["cams"][c] = {
            "img_shape": list(rgb.shape), "K": np.round(cam.data.intrinsic_matrices[0].cpu().numpy(), 2).tolist(),
            "pos_w": np.round(cam.data.pos_w[0].cpu().numpy(), 4).tolist(),
            "quat_w_world": np.round(cam.data.quat_w_world[0].cpu().numpy(), 4).tolist(),
            "depth_valid_frac": round(float(np.isfinite(dep).mean()), 3),
            "depth_range_m": [round(float(fin.min()), 3), round(float(fin.max()), 3)] if fin.size else None,
            "png_bytes": _save_png(rgb, f"{out}/scene_{tag}_seed0_{SHORT[c]}.png")}
        _save_png(_depth_vis(dep), f"{out}/scene_{tag}_seed0_{SHORT[c]}_depth.png")
    print("BOOT_RESULT " + json.dumps(res), flush=True)
    with open(f"{out}/boot_seed0_{'_'.join(SHORT[c] for c in cams)}_{sim_device}.json", "w") as f:
        json.dump(res, f, indent=1)


def dev(out: str, kind: str, seeds, frames: bool, sim_device: str = "cpu"):
    from .planner import run_episode
    from .scene import make_env
    os.makedirs(out, exist_ok=True)
    from .scene import RECORD_CAMERAS
    cams = RECORD_CAMERAS if frames else ()
    env = None
    path = f"{out}/dev_{kind}.jsonl"
    for s in seeds:
        if env is None:
            env = make_env(s, headless=True, cameras=cams, depth=False, sim_device=sim_device)
        else:
            env.set_seed(s)
        shots = []

        def on_step(e, pl, _last=[None]):
            if frames and pl.phase != _last[0]:
                _last[0] = pl.phase
                shots.append((pl.phase, [e.camera_rgb(c) for c in cams]))

        r = run_episode(env, kind=kind, seed=s, on_step=on_step if frames else None)
        pl = r.pop("planner")
        r["sim_device"] = env.sim_device
        r["decision_points_head"] = [(round(t, 2), d, a) for t, d, a in __import__(
            "harvest.sim.planner", fromlist=["decision_points"]).decision_points(pl)[:3]]
        print("EP " + json.dumps(r), flush=True)
        with open(path, "a") as f:
            f.write(json.dumps(r) + "\n")
        if frames and shots:
            from PIL import Image, ImageDraw
            for ci, c in enumerate(cams):
                w = 336
                h0, w0 = shots[0][1][ci].shape[:2]
                h = int(round(w * h0 / w0))
                n = len(shots)
                sheet = Image.new("RGB", (w * min(n, 4), h * ((n + 3) // 4)))
                for i, (ph, imgs) in enumerate(shots):
                    im = Image.fromarray(imgs[ci]).resize((w, h))
                    ImageDraw.Draw(im).text((5, 5), ph, fill=(255, 255, 0))
                    sheet.paste(im, ((i % 4) * w, (i // 4) * h))
                sheet.save(f"{out}/frames_{kind}_s{s}_{SHORT[c]}.png", optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["boot", "dev"])
    ap.add_argument("--out", default="/data/harvest/out/t11_12")
    ap.add_argument("--kind", default="P0", choices=["P0", "P1", "P2"])
    ap.add_argument("--seeds", default="0-29")
    ap.add_argument("--frames", action="store_true")
    ap.add_argument("--sim-device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--cams", default="cam_head,cam_wrist_right", help="boot: cameras to render")
    a = ap.parse_args()
    if a.mode == "boot":
        boot(a.out, tuple(a.cams.split(",")), sim_device=a.sim_device)
    else:
        dev(a.out, a.kind, _seeds(a.seeds), a.frames, sim_device=a.sim_device)
    os._exit(0)  # SimulationApp.close() hangs in this chroot; results are already flushed


if __name__ == "__main__":
    main()
