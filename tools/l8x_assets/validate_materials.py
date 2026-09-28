"""Render check of the CC0 material library (pod, Isaac; b4, user-log 173): the L8 table scene with a wood material
bound to the table, a floor material on the ground plane and an indoor HDRI on the dome light, one combination per
seed (materials.pick, train split); head-camera frame per seed -> <out>/mat_<seed>.png and a JSON of the choices.
usage: python -m tools.l8x_assets.validate_materials --out DIR [--seeds 0,1,2,3,4,5]"""
from __future__ import annotations

import argparse
import json
import os


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="0,1,2,3,4,5")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.sim.assets_x import materials as M
        from tools.l8x_assets.validate import _save
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        env.reset(settle_s=0.2)
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        cat = M.usable(M.load())
        os.makedirs(a.out, exist_ok=True)
        log = {}
        for s in (int(v) for v in a.seeds.split(",")):
            wood, floor, env_ = (M.pick(cat, r, s) for r in ("furniture", "floor", "env"))
            mt = M.author(stage, f"/World/Looks/b4_wood_{s}", wood, uv_scale=(1.0, 1.0))
            mf = M.author(stage, f"/World/Looks/b4_floor_{s}", floor, uv_scale=(20.0, 20.0))
            M.bind(stage.GetPrimAtPath("/World/envs/env_0/Table"), mt)
            M.bind(stage.GetPrimAtPath("/World/GroundPlane"), mf)
            M.set_dome(stage, "/World/light", env_)
            for _ in range(20):
                env.env.sim.render()
            env.scene["cam_head"].update(0.0, force_recompute=True)
            _save(env.camera_rgb("cam_head").copy(), os.path.join(a.out, f"mat_{s}.png"))
            log[s] = {"furniture": wood["id"], "floor": floor["id"], "env": env_["id"]}
            print("MAT " + json.dumps({"seed": s, **log[s]}), flush=True)
        json.dump(log, open(os.path.join(a.out, "materials_check.json"), "w"), indent=1)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
