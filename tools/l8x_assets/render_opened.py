"""Render check of the baked opened fixtures (bake_open.py; pod, Isaac): each static opened copy in turn stands on
the floor in front of the robot (yaw -90 deg, front towards the robot, its front 0.45 m ahead), lift lowered, head
camera frame -> <out>/open_<name>.png.
usage: python -m tools.l8x_assets.render_opened --opened opened.json --out DIR [--names a,b]"""
from __future__ import annotations

import argparse
import json
import math
import os

PARK = (-8.0, -8.0, -5.0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--opened", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--names", default="")
    ap.add_argument("--z", type=float, default=0.0, help="base height (small pieces: raise into view)")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.sim.randomize import _set_pose
        from tools.l8x_assets.validate import _save
        rows = {k: r for k, r in json.load(open(a.opened)).items() if "error" not in r}
        names = [n for n in (a.names.split(",") if a.names else sorted(rows)) if n in rows]
        orig = SC._build_cfg

        def patched(*x, **k):
            import isaaclab.sim as sim_utils
            from isaaclab.assets import AssetBaseCfg
            cfg, layout = orig(*x, **k)
            cfg.scene.table = None
            for i, n in enumerate(names):
                setattr(cfg.scene, f"op{i}", AssetBaseCfg(
                    prim_path="{ENV_REGEX_NS}/OP_%d" % i, spawn=sim_utils.UsdFileCfg(usd_path=rows[n]["dst"]),
                    init_state=AssetBaseCfg.InitialStateCfg(pos=(PARK[0] - 3.0 * i, PARK[1], PARK[2]))))
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        env.layout = {}
        SC._LAYOUT["layout"] = {}
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        os.makedirs(a.out, exist_ok=True)
        yaw = -math.pi / 2
        q = (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))
        for i, n in enumerate(names):
            for j in range(len(names)):
                p = stage.GetPrimAtPath("/World/envs/env_0/OP_%d" % j)
                if j == i:
                    sx, sy, _ = rows[n]["collider_size"]  # after yaw -90 the asset's y depth runs along world x
                    _set_pose(p, (0.45 + sy / 2, -0.2, a.z), q)
                else:
                    _set_pose(p, (PARK[0] - 3.0 * j, PARK[1], PARK[2]), (1.0, 0.0, 0.0, 0.0))
            env.reset(settle_s=0.1)
            for _ in range(12):
                env.env.sim.render()
            env.scene["cam_head"].update(0.0, force_recompute=True)
            _save(env.camera_rgb("cam_head").copy(), os.path.join(a.out, f"open_{n}.png"))
            print("RENDER", n, flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
