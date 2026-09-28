"""Render check of textured parametric furniture (b4; pod, Isaac): parametric furniture scenes (furniture.sample_scene
kinds) with the cuboid slots' UV render meshes, a b4 wood material bound to every used slot and a floor material
on the ground; head-camera frame per (kind, seed) -> <out>/fxuv_<kind>_<seed>.png.
usage: python -m tools.l8x_assets.validate_fx_uv --out DIR [--kinds table,counter,shelf_low] [--seeds 0,1]"""
from __future__ import annotations

import argparse
import os


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--kinds", default="table,counter,shelf_low")
    ap.add_argument("--seeds", default="0,1")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.sim.assets_x import furniture as FU
        from harvest.sim.assets_x import isaac as FX
        from harvest.sim.assets_x import materials as M
        from tools.l8x_assets.validate import _save
        FX.without_table()
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        env.layout = {}
        SC._LAYOUT["layout"] = {}
        env.reset(settle_s=0.2)
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        cat = M.usable(M.load())
        wood = M.author(stage, "/World/Looks/b4_furniture", M.pick(cat, "furniture", 0), uv_scale=(2.0, 2.0))
        floor = M.author(stage, "/World/Looks/b4_floor", M.pick(cat, "floor", 0), uv_scale=(2.0, 2.0))
        for i in range(FX.N_SLOTS):
            M.bind(stage.GetPrimAtPath(FX._slot_path(i)), wood)
        M.bind(stage.GetPrimAtPath("/World/GroundPlane"), floor)
        os.makedirs(a.out, exist_ok=True)
        for kind in a.kinds.split(","):
            for s in (int(v) for v in a.seeds.split(",")):
                sc = FU.sample_scene(kind, s)
                FX.author_scene(env, sc)
                M.retexture(stage, "/World/Looks/b4_furniture", M.pick(cat, "furniture", s))
                env.reset(settle_s=0.2)
                for _ in range(20):
                    env.env.sim.render()
                env.scene["cam_head"].update(0.0, force_recompute=True)
                _save(env.camera_rgb("cam_head").copy(), os.path.join(a.out, f"fxuv_{kind}_{s}.png"))
                print("FXUV", kind, s, flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
