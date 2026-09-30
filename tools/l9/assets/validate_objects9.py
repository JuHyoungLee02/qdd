"""L9 copy of tools/l8x_assets/validate_objects.py (same stable rule and settle) with size-aware batches: objects
with footprint_r <= 0.07 m go 12 per batch on the 3 x 4 grid (as before), <= 0.13 m 4 per batch (2 x 2 grid on the
region corners), larger ones 2 per batch (the two far ends) -- big places (trays, baskets, bins) no longer shove
their neighbours (the L8S grid made 40 % of the L9 place rows fail by contact, not by instability).
Original header follows.
L8X-assets object check (pod, Isaac): Objaverse objects (objv_table.py output) as dynamic rigid bodies (their own
convex-hull colliders, usd_physics) on a parametric table, 12 per batch on a grid, 2 s settle:
  stable   |bottom - table top| <= 5 mm, tilt change <= 10 deg, drift <= 2 cm
  render   head-camera frame per batch with the object names (contact sheet), video of the settle
usage: python -m tools.l8x_assets.validate_objects --table objects.json --out DIR [--n 48] [--seed 0]"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

PER_BATCH = 12
SETTLE_TICKS = 40
PARK = (-5.0, 5.0, 0.2)


def _r(v, n=4):
    return round(float(v), n)


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def tilt_deg(q, q0):
    """Angle the object turned away from its placed upright: the local axis that pointed up at placement (q0)
    against world z after the settle (q). Works for Y-up (MolmoSpaces) and z-up (GSO) geometry alike."""
    up_local = qmat(q0).T @ np.array([0.0, 0.0, 1.0])
    return math.degrees(math.acos(float(np.clip((qmat(q) @ up_local)[2], -1.0, 1.0))))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=48)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    code = 0
    try:

        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.sim.assets_x import furniture as FU
        from harvest.sim.assets_x.isaac import author_scene, slot_cfgs
        from tools.l8x_assets.validate import _save, _video

        objs = json.load(open(a.table))["objects"]
        objs = {k: o for k, o in objs.items() if o.get("usd_physics")}
        names = sorted(objs)
        rng = np.random.default_rng([a.seed, 5])
        pick = [names[i] for i in sorted(rng.choice(len(names), size=min(a.n, len(names)), replace=False))]
        orig = SC._build_cfg

        def patched(*x, **k):  # runs inside make_env, after the app started (isaaclab imports need it)
            import isaaclab.sim as sim_utils
            from isaaclab.assets import RigidObjectCfg
            cfg, layout = orig(*x, **k)
            cfg.scene.table = None
            for n, c in slot_cfgs(None).items():
                setattr(cfg.scene, n, c)
            for i, n in enumerate(pick):
                o = objs[n]
                setattr(cfg.scene, "ob_" + n, RigidObjectCfg(
                    prim_path="{ENV_REGEX_NS}/OB_" + n,
                    spawn=sim_utils.UsdFileCfg(usd_path=o["usd_physics"],
                                               mass_props=sim_utils.MassPropertiesCfg(mass=o["mass"])),
                    init_state=RigidObjectCfg.InitialStateCfg(pos=(PARK[0] - 0.6 * i, PARK[1], PARK[2]),
                                                              rot=tuple(o["spawn_quat_wxyz"]))))
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        sc = FU.sample_scene("table", 3)
        top = sc["surfaces"][0]["top_z"]
        (x0, x1), (y0, y1) = sc["surfaces"][0]["xy_box"]
        author_scene(env, sc)
        env.layout = {}
        SC._LAYOUT["layout"] = {}
        env.reset(settle_s=0.5)
        os.makedirs(a.out, exist_ok=True)
        res = {}
        gx = np.linspace(max(x0 + 0.08, 0.34), min(x1 - 0.08, 0.66), 3)
        gy = np.linspace(max(y0 + 0.08, -0.55), min(y1 - 0.08, 0.15), 4)
        slots = [(x, y) for x in gx for y in gy]
        slots4 = [(x, y) for x in (gx[0], gx[-1]) for y in (gy[0], gy[-1])]
        slots2 = [((gx[0] + gx[-1]) / 2, gy[0]), ((gx[0] + gx[-1]) / 2, gy[-1])]
        batches = []
        for lim, per, sl in ((0.07, PER_BATCH, slots), (0.13, 4, slots4), (9.0, 2, slots2)):
            lo = {0.07: -1.0, 0.13: 0.07, 9.0: 0.13}[lim]
            grp = [n for n in pick if lo < objs[n]["footprint_r"] <= lim]
            batches += [(grp[i:i + per], sl) for i in range(0, len(grp), per)]
        for b, (batch, slots) in enumerate(batches):
            b = b * PER_BATCH
            frames, placed = [], {}
            for (x, y), n in zip(slots, batch):
                o = objs[n]
                yaw = float(rng.uniform(-math.pi, math.pi))
                q = qmul((math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)), tuple(o["spawn_quat_wxyz"]))
                cx, cy = o["centre_from_root_xy"]
                c, s = math.cos(yaw), math.sin(yaw)
                rx, ry = x - (c * cx - s * cy), y - (s * cx + c * cy)
                z = top + o["root_above_bottom"] + 0.005
                env.scene["ob_" + n].write_root_pose_to_sim(
                    env.torch.tensor([[rx, ry, z, *q]], dtype=env.torch.float32, device=env.env.device))
                env.scene["ob_" + n].write_root_velocity_to_sim(env.torch.zeros((1, 6), device=env.env.device))
                placed[n] = (rx, ry, z, q)
            hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
            for t in range(SETTLE_TICKS):
                env.step(hold)
                if t % 4 == 0:
                    env.env.sim.render()
                    env.scene["cam_head"].update(0.0, force_recompute=True)
                    frames.append(env.camera_rgb("cam_head").copy())
            for n, (rx, ry, z, q) in placed.items():
                d = env.scene["ob_" + n].data
                p = d.root_pos_w[0].cpu().numpy()
                qq = d.root_quat_w[0].cpu().numpy()
                dz = p[2] - (z - 0.005)
                res[n] = {"dz_mm": _r(dz * 1e3, 1), "drift_mm": _r(math.hypot(p[0] - rx, p[1] - ry) * 1e3, 1),
                          "tilt_deg": _r(tilt_deg(qq, q), 1), "category": objs[n]["category"],
                          "height": objs[n]["height"], "grasp_width": objs[n]["grasp_width"]}
                res[n]["stable"] = bool(abs(dz) <= 0.005 and res[n]["tilt_deg"] <= 10 and res[n]["drift_mm"] <= 20)
                env.scene["ob_" + n].write_root_pose_to_sim(env.torch.tensor(
                    [[PARK[0] - 0.6 * pick.index(n), PARK[1], PARK[2], *objs[n]["spawn_quat_wxyz"]]],
                    dtype=env.torch.float32, device=env.env.device))
            _video(frames, os.path.join(a.out, f"batch{b // PER_BATCH}.mp4"))
            _save(frames[-1], os.path.join(a.out, f"batch{b // PER_BATCH}.png"))
            print("BATCH " + json.dumps({k: res[k] for k in batch}), flush=True)
        with open(os.path.join(a.out, "objects_check.json"), "w") as f:
            json.dump(res, f, indent=1)
        print("OBJ_DONE", sum(v["stable"] for v in res.values()), "/", len(res), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
