"""Display gate for b4 (user-log 175; pod, Isaac): products on fixture shelves and objects on products.

  shelf    every fixture (assets_ph.json rows, static triangle-mesh colliders) stands in its own spot far from the
           robot; on each of its support surfaces (surfaces.transform_surface of the asset's surfaces) up to
           PER_SURF products are placed 5 mm above the surface on a grid inside the region shrunk by 3 cm, 2 s settle;
           a product is stable when |bottom - top| <= 5 mm, tilt <= 10 deg, drift <= 2 cm; a surface passes with
           >= 75 % stable, a fixture with >= 1 passing surface ("display_ok", with its passing surface ids).
  stack    products with a top surface stand on the floor, each with a small object (the smallest stable product,
           a different one per base) centred on its top surface; both stable after the settle = "stack_base_ok".
Output <out>/display_check.json {fixtures: {...}, stack: {...}} + head-camera frames of each fixture.
usage: python -m tools.l8x_assets.gate_display --fixtures F.json --products P.json --out DIR"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

PER_SURF = 4
SETTLE = 40
SPOT_DX, SPOT_Y0, SPOT_DY = 3.0, -6.0, 3.0  # fixture k stands at (SPOT_DX, SPOT_Y0 + k * SPOT_DY)
STACK_Y = 12.0
PARK = (-6.0, 6.0, 0.3)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--products", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-products", type=int, default=160)
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.sim.assets_x import surfaces as SU
        from tools.l8x_assets.validate import _save
        from tools.l8x_assets.validate_objects import qmul, tilt_deg

        fx = json.load(open(a.fixtures))["assets"]
        pr = {k: o for k, o in json.load(open(a.products))["objects"].items()
              if o.get("usd_physics") and o.get("stable") is not False}
        names = sorted(pr)[:a.max_products]
        fnames = sorted(fx)
        orig = SC._build_cfg

        def patched(*x, **k):
            import isaaclab.sim as sim_utils
            from isaaclab.assets import AssetBaseCfg, RigidObjectCfg
            cfg, layout = orig(*x, **k)
            cfg.scene.table = None
            for i, n in enumerate(fnames):
                f = fx[n]
                yaw = float(f.get("yaw", -math.pi / 2))
                setattr(cfg.scene, f"fx_{i}", AssetBaseCfg(
                    prim_path="{ENV_REGEX_NS}/FX_%d" % i, spawn=sim_utils.UsdFileCfg(usd_path=f["dst"]),
                    init_state=AssetBaseCfg.InitialStateCfg(pos=(SPOT_DX, SPOT_Y0 + i * SPOT_DY, 0.0),
                                                            rot=(math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)))))
            for i, n in enumerate(names):
                o = pr[n]
                setattr(cfg.scene, "pr_%d" % i, RigidObjectCfg(
                    prim_path="{ENV_REGEX_NS}/PR_%d" % i,
                    spawn=sim_utils.UsdFileCfg(usd_path=o["usd_physics"],
                                               mass_props=sim_utils.MassPropertiesCfg(mass=o["mass"])),
                    init_state=RigidObjectCfg.InitialStateCfg(pos=(PARK[0] - 0.4 * i, PARK[1], PARK[2]),
                                                              rot=tuple(o["spawn_quat_wxyz"]))))
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        env.layout = {}
        SC._LAYOUT["layout"] = {}
        env.reset(settle_s=0.2)
        T = env.torch
        dev = env.env.device

        def put(i, x, y, bottom_z, yaw=0.0):
            o = pr[names[i]]
            q = qmul((math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)), tuple(o["spawn_quat_wxyz"]))
            cx, cy = o["centre_from_root_xy"]
            c, s = math.cos(yaw), math.sin(yaw)
            rx, ry, z = x - (c * cx - s * cy), y - (s * cx + c * cy), bottom_z + o["root_above_bottom"] + 0.005
            env.scene["pr_%d" % i].write_root_pose_to_sim(T.tensor([[rx, ry, z, *q]], dtype=T.float32, device=dev))
            env.scene["pr_%d" % i].write_root_velocity_to_sim(T.zeros((1, 6), device=dev))
            return rx, ry, z, q

        def park(i):
            o = pr[names[i]]
            env.scene["pr_%d" % i].write_root_pose_to_sim(T.tensor(
                [[PARK[0] - 0.4 * i, PARK[1], PARK[2], *o["spawn_quat_wxyz"]]], dtype=T.float32, device=dev))

        def settle():
            hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
            for _ in range(SETTLE):
                env.step(hold)

        def judge(i, placed):
            rx, ry, z, q = placed
            d = env.scene["pr_%d" % i].data
            p, qq = d.root_pos_w[0].cpu().numpy(), d.root_quat_w[0].cpu().numpy()
            dz, dr, tl = p[2] - (z - 0.005), math.hypot(p[0] - rx, p[1] - ry), tilt_deg(qq, q)
            return {"dz_mm": round(dz * 1e3, 1), "drift_mm": round(dr * 1e3, 1), "tilt_deg": round(tl, 1),
                    "stable": bool(abs(dz) <= 0.005 and tl <= 10 and dr <= 0.02)}

        os.makedirs(a.out, exist_ok=True)
        res = {"fixtures": {}, "stack": {}}
        nxt = 0
        for k, n in enumerate(fnames):
            f = fx[n]
            pos = (SPOT_DX, SPOT_Y0 + k * SPOT_DY, 0.0)
            placed, where = {}, {}
            for si, s in enumerate(f["surfaces"]):
                t = SU.transform_surface(s, pos=pos, yaw=float(f.get("yaw", -math.pi / 2)))
                (x0, x1), (y0, y1) = t["xy_box"]
                x0, x1, y0, y1 = x0 + 0.03, x1 - 0.03, y0 + 0.03, y1 - 0.03
                if x1 <= x0 or y1 <= y0:
                    continue
                room = t["clearance"] if t.get("clearance") is not None else 1.0
                cols = max(1, min(PER_SURF, int((y1 - y0) / 0.12)))
                for j in range(cols):
                    for _ in range(len(names)):
                        i = nxt % len(names)
                        nxt += 1
                        o = pr[names[i]]
                        if i not in placed and o["height"] < room - 0.02 and 2 * o["footprint_r"] < min(x1 - x0,
                                                                                                          0.3):
                            break
                    else:
                        continue
                    y = y0 + (j + 0.5) * (y1 - y0) / cols
                    placed[i] = put(i, (x0 + x1) / 2, y, t["top_z"])
                    where[i] = s.get("id", si)
            settle()
            env.env.sim.render()
            surf = {}
            for i, pl in placed.items():
                r = judge(i, pl)
                surf.setdefault(str(where[i]), []).append(dict(r, product=names[i]))
                park(i)
            ok_s = [sid for sid, rs in surf.items() if sum(r["stable"] for r in rs) >= 0.75 * len(rs)]
            res["fixtures"][n] = {"surfaces": surf, "ok_surfaces": ok_s, "display_ok": bool(ok_s)}
            print("FIX " + json.dumps({"fixture": n, "ok_surfaces": len(ok_s), "n_surfaces": len(surf)}), flush=True)
        # objects on products (on the floor, far from the robot)
        bases = [i for i, n in enumerate(names) if pr[n].get("top_surface")]
        small = sorted(range(len(names)), key=lambda i: pr[names[i]]["height"] * pr[names[i]]["grasp_width"])
        for b0 in range(0, len(bases), 16):
            batch, placed = bases[b0:b0 + 16], {}
            used = set(batch)
            for j, i in enumerate(batch):
                x, y = SPOT_DX + 0.5 * (j % 4), STACK_Y + 0.5 * (j // 4)
                placed[i] = ("base", put(i, x, y, 0.0), None)
                ts = pr[names[i]]["top_surface"]  # canonical frame: box [[x0, x1], [y0, y1]], top_z above bottom
                (bx0, bx1), (by0, by1) = ts["box"]
                top = next((s for s in small if s not in used and 2 * pr[names[s]]["footprint_r"] <
                            min(bx1 - bx0, by1 - by0)), None)
                if top is not None:
                    used.add(top)
                    placed[top] = ("top", put(top, x + (bx0 + bx1) / 2, y + (by0 + by1) / 2, float(ts["top_z"])), i)
            settle()
            for i, (role, pl, base) in placed.items():
                r = judge(i, pl)
                if role == "base":
                    res["stack"].setdefault(names[i], {})["base"] = r
                else:
                    res["stack"].setdefault(names[base], {})["top"] = dict(r, product=names[i])
            for i in placed:
                park(i)
        for n, r in res["stack"].items():
            r["stack_base_ok"] = bool(r.get("base", {}).get("stable") and r.get("top", {}).get("stable"))
        json.dump(res, open(os.path.join(a.out, "display_check.json"), "w"), indent=1)
        print("DISPLAY_DONE", sum(v["display_ok"] for v in res["fixtures"].values()), "/", len(res["fixtures"]),
              "stack", sum(v["stack_base_ok"] for v in res["stack"].values()), "/", len(res["stack"]), flush=True)
        _ = _save
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
