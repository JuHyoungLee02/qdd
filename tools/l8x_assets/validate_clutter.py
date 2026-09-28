"""L8X-assets clutter check (pod, Isaac): furniture scenes with 5-12 real objects (clutter.sample_clutter over the
objects whose settle check passed), 2 s settle, per scene: objects that tipped (> 10 deg), slid (> 2 cm) or sank /
floated (> 5 mm), final footprint overlaps; head-camera frame + video.
usage: python -m tools.l8x_assets.validate_clutter --table real_objects.json --out DIR --kinds a,b --seeds 0,1,2"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

from tools.l8x_assets.validate_objects import PARK, qmul, tilt_deg

SETTLE_TICKS = 40


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--kinds", default="table,counter,shelf_low,multi_level")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--reach", default="/data/harvest/out/teach_l8d/gate/reach_base.json")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.sim.assets_x import clutter as CL
        from harvest.sim.assets_x import furniture as FU
        from harvest.sim.assets_x.isaac import author_scene, slot_cfgs
        from harvest.sim.assets_x.reach import ReachModel
        from tools.l8x_assets.validate import _save, _video

        objs = {k: o for k, o in json.load(open(a.table))["objects"].items() if o.get("stable")}
        rm = ReachModel.load(a.reach)
        plans = []
        for kind in a.kinds.split(","):
            for s in (int(x) for x in a.seeds.split(",")):
                sc = FU.sample_scene(kind, s, reach=rm)
                keep = [p["region"] for p in sc["placement_regions"] if p["region"]][:1]
                plans.append((sc, CL.sample_clutter(sc, objs, s, keep_free=keep)))
        used = sorted({p["id"] for _, c in plans for p in c["placements"]})
        orig = SC._build_cfg

        def patched(*x, **k):
            import isaaclab.sim as sim_utils
            from isaaclab.assets import RigidObjectCfg
            cfg, layout = orig(*x, **k)
            cfg.scene.table = None
            for n, c in slot_cfgs(None).items():
                setattr(cfg.scene, n, c)
            for i, n in enumerate(used):
                o = objs[n]
                setattr(cfg.scene, "ob_" + n, RigidObjectCfg(
                    prim_path="{ENV_REGEX_NS}/OB_" + n,
                    spawn=sim_utils.UsdFileCfg(usd_path=o["usd_physics"],
                                               mass_props=sim_utils.MassPropertiesCfg(mass=o["mass"])),
                    init_state=RigidObjectCfg.InitialStateCfg(pos=(PARK[0] - 0.3 * i, PARK[1], PARK[2]),
                                                              rot=tuple(o["spawn_quat_wxyz"]))))
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        os.makedirs(a.out, exist_ok=True)
        summary = []
        dev, T = env.env.device, env.torch
        for sc, cl in plans:
            author_scene(env, sc)
            env.layout = {}
            SC._LAYOUT["layout"] = {}
            env.reset(settle_s=0.3)
            placed = {}
            for p in cl["placements"]:
                o = objs[p["id"]]
                q = qmul((math.cos(p["yaw"] / 2), 0, 0, math.sin(p["yaw"] / 2)), tuple(o["spawn_quat_wxyz"]))
                cx, cy = o["centre_from_root_xy"]
                c, s = math.cos(p["yaw"]), math.sin(p["yaw"])
                rx, ry = p["x"] - (c * cx - s * cy), p["y"] - (s * cx + c * cy)
                z = p["z_root"] + 0.005
                env.scene["ob_" + p["id"]].write_root_pose_to_sim(T.tensor([[rx, ry, z, *q]], dtype=T.float32,
                                                                           device=dev))
                env.scene["ob_" + p["id"]].write_root_velocity_to_sim(T.zeros((1, 6), device=dev))
                placed[p["id"]] = (rx, ry, z - 0.005, q, p)
            hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
            frames = []
            for t in range(SETTLE_TICKS):
                env.step(hold)
                if t % 4 == 0:
                    env.env.sim.render()
                    env.scene["cam_head"].update(0.0, force_recompute=True)
                    frames.append(env.camera_rgb("cam_head").copy())
            bad, fin = [], []
            for n, (rx, ry, z, q, p) in placed.items():
                d = env.scene["ob_" + n].data
                pos, qq = d.root_pos_w[0].cpu().numpy(), d.root_quat_w[0].cpu().numpy()
                tilt, drift, dz = tilt_deg(qq, q), math.hypot(pos[0] - rx, pos[1] - ry), pos[2] - z
                if tilt > 10 or drift > 0.02 or abs(dz) > 0.005:
                    bad.append({"id": n, "tilt": round(tilt, 1), "drift_mm": round(drift * 1e3, 1),
                                "dz_mm": round(dz * 1e3, 1)})
                fin.append(dict(p, x=float(p["x"] + pos[0] - rx), y=float(p["y"] + pos[1] - ry)))
            ov = CL.overlaps(fin)
            tag = f"{sc['kind']}_s{sc['seed']}"
            _save(frames[-1], os.path.join(a.out, tag + ".png"))
            _video(frames, os.path.join(a.out, tag + ".mp4"))
            r = {"scene": tag, "n_target": cl["n_target"], "n_placed": cl["n_placed"], "moved": bad,
                 "overlaps_after": ov, "ok": not bad and not ov}
            summary.append(r)
            print("CLUTTER " + json.dumps(r), flush=True)
            for n in placed:  # park again for the next scene
                i = used.index(n)
                env.scene["ob_" + n].write_root_pose_to_sim(T.tensor(
                    [[PARK[0] - 0.3 * i, PARK[1], PARK[2], *objs[n]["spawn_quat_wxyz"]]], dtype=T.float32, device=dev))
        with open(os.path.join(a.out, "clutter_check.json"), "w") as f:
            json.dump(summary, f, indent=1)
        print("CLUTTER_DONE", sum(r["ok"] for r in summary), "/", len(summary), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
