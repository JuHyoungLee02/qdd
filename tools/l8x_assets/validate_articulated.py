"""Articulated THOR furniture test (prereg_l8x_tasks 2.3, pod Isaac; no data): per asset, spawned as a fixed-root
articulation with its drawer (prismatic) joints kept, drawer links 1 kg, joints damped:
  spawn   every drawer joint stays within 5 mm of its start for 2 s (the drawers do not drift open or fall out)
  handle  the handle bodies (name contains 'handle') and their world poses, matched to a drawer by distance
  pull    20 N along the drawer's slide axis on one drawer link for 1 s -> its joint opens > 10 cm (both axis signs are
          tried: the one that increases the joint value is the opening direction)
usage: python -m tools.l8x_assets.validate_articulated --out DIR --assets a.usda,b.usda,..."""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

PARK = (6.0, 6.0, 0.0)
SPACING = 2.5


def joints_of(usd: str) -> dict:
    """{joint name: {type, body0, body1, lower, upper}} from the USD (pxr)."""
    from pxr import Usd
    out = {}
    st = Usd.Stage.Open(usd)  # keep the stage alive while traversing
    for p in st.Traverse():
        t = p.GetTypeName()
        if t in ("PhysicsPrismaticJoint", "PhysicsRevoluteJoint"):
            b0 = p.GetRelationship("physics:body0").GetTargets()
            b1 = p.GetRelationship("physics:body1").GetTargets()
            lo, hi = p.GetAttribute("physics:lowerLimit").Get(), p.GetAttribute("physics:upperLimit").Get()
            ax = str(p.GetAttribute("physics:axis").Get() or "X")
            e = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}[ax]
            axes = []
            for s in ("0", "1"):
                q = p.GetAttribute(f"physics:localRot{s}").Get()
                axes.append([float(v) for v in (_qrot((q.GetReal(), *q.GetImaginary()), e) if q is not None
                                                else np.array(e))])
            out[p.GetName()] = {"type": t, "body0": str(b0[0].name) if b0 else None,
                                "body1": str(b1[0].name) if b1 else None, "lower": lo, "upper": hi,
                                "axis_body0": axes[0], "axis_body1": axes[1]}
    # the carcass is the body most joints share; the drawer is the joint's other body (either side in THOR files)
    count: dict = {}
    for j in out.values():
        for b in (j["body0"], j["body1"]):
            count[b] = count.get(b, 0) + 1
    for j in out.values():
        side = "1" if count.get(j["body0"], 0) >= count.get(j["body1"], 0) and len(out) > 1 else "0"
        j["drawer"], j["axis_drawer"] = j["body" + side], j["axis_body" + side]
    return out


def _qrot(q, v):
    w, x, y, z = (float(c) for c in q)
    u = np.array([x, y, z])
    v = np.asarray(v, float)
    return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--assets", required=True)
    ap.add_argument("--force", type=float, default=20.0)
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from tools.l8x_assets.validate import _save
        usds = a.assets.split(",")
        names = [os.path.splitext(os.path.basename(u))[0] for u in usds]

        orig = SC._build_cfg
        qy = (0.7071068, 0.7071068, 0.0, 0.0)  # THOR Y-up -> Z-up

        def patched(*x, **k):
            import isaaclab.sim as sim_utils
            from isaaclab.actuators import ImplicitActuatorCfg
            from isaaclab.assets import ArticulationCfg
            cfg, layout = orig(*x, **k)
            for i, (n, u) in enumerate(zip(names, usds)):
                setattr(cfg.scene, "art_" + n, ArticulationCfg(
                    prim_path="{ENV_REGEX_NS}/ART_" + n,
                    spawn=sim_utils.UsdFileCfg(
                        usd_path=u, mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
                        articulation_props=sim_utils.ArticulationRootPropertiesCfg(fix_root_link=True)),
                    init_state=ArticulationCfg.InitialStateCfg(pos=(1.5 + SPACING * i, 2.5, 0.0), rot=qy),
                    actuators={"drawers": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=0.0, damping=20.0)}))
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        jinfo = {n: joints_of(u) for n, u in zip(names, usds)}  # pxr: only after the app started
        env.reset(settle_s=0.2)
        T, dev = env.torch, env.env.device
        hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
        res = {}
        for n in names:
            art = env.scene["art_" + n]
            jn = list(art.joint_names)
            q0 = art.data.joint_pos[0].cpu().numpy().copy()
            for _ in range(40):  # 2 s
                env.step(hold)
            q1 = art.data.joint_pos[0].cpu().numpy()
            pris = [j for j in jn if jinfo[n].get(j, {}).get("type") == "PhysicsPrismaticJoint"]
            drift = {j: round(float(abs(q1[jn.index(j)] - q0[jn.index(j)])) * 1000, 1) for j in pris}
            bn = list(art.body_names)
            bp = art.data.body_pos_w[0].cpu().numpy()
            handles = {b: [round(float(v), 3) for v in bp[bn.index(b)]] for b in bn if "handle" in b.lower()}
            r = {"n_joints": len(jn), "prismatic": len(pris), "spawn_drift_mm": drift,
                 "spawn_ok": bool(pris) and max(drift.values()) <= 5.0, "handles": handles, "pull": None}
            tries = []  # up to 4 drawers x 2 signs at the registered force; then 3x force on the best-scoring one
            for j in pris[:4]:
                drawer = jinfo[n][j]["drawer"]
                bi = bn.index(drawer) if drawer in bn else None
                for sign in (1.0, -1.0):
                    if bi is None:
                        break
                    for force in (a.force,):
                        env.reset(settle_s=0.2)
                        f = T.zeros((1, len(bn), 3), device=dev)
                        ax = jinfo[n][j]["axis_drawer"]  # the joint axis in the drawer body frame (its localRot)
                        f[0, bi, :] = T.tensor([sign * force * c for c in ax], device=dev)
                        art.set_external_force_and_torque(f, T.zeros_like(f))
                        qa = float(art.data.joint_pos[0, jn.index(j)])
                        for _ in range(20):  # 1 s
                            env.step(hold)
                        qb = float(art.data.joint_pos[0, jn.index(j)])
                        art.set_external_force_and_torque(T.zeros_like(f), T.zeros_like(f))
                        tries.append({"joint": j, "drawer": drawer, "sign": sign, "force_n": force,
                                      "opened_m": round(qb - qa, 4),
                                      "limit": [jinfo[n][j]["lower"], jinfo[n][j]["upper"]]})
            r["pull_tries"] = tries
            r["pull"] = max(tries, key=lambda t: abs(t["opened_m"])) if tries else None
            r["pull_ok"] = bool(r["pull"]) and abs(r["pull"]["opened_m"]) > 0.10
            if not handles and r["pull"]:  # handle inside the drawer mesh: the drawer front centre, from its bbox
                handles = {"front_of_" + r["pull"]["drawer"]: _front(env, n, r["pull"]["drawer"], art, bn)}
                r["handles"] = handles
                r["handle_from"] = "drawer front (no separate handle body)"
            r["pass"] = r["spawn_ok"] and bool(handles) and r["pull_ok"]
            res[n] = r
            print("ART " + json.dumps({n: r}), flush=True)
        env.env.sim.render()
        env.scene["cam_head"].update(0.0, force_recompute=True)
        os.makedirs(a.out, exist_ok=True)
        _save(env.camera_rgb("cam_head"), os.path.join(a.out, "head.png"))
        with open(os.path.join(a.out, "articulated.json"), "w") as f:
            json.dump(res, f, indent=1)
        print("ART_DONE", sum(r["pass"] for r in res.values()), "/", len(res), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)




def _front(env, n, drawer, art, bn):
    """The drawer body world bbox centre moved to its face nearest the robot (min world x): the grip point."""
    import omni.usd
    from pxr import Usd, UsdGeom
    st = omni.usd.get_context().get_stage()
    root = st.GetPrimAtPath(f"/World/envs/env_0/ART_{n}")
    for p in Usd.PrimRange(root):
        if p.GetName() == drawer:
            r = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(p).ComputeAlignedRange()
            lo, hi = np.array(r.GetMin()), np.array(r.GetMax())
            c = (lo + hi) / 2
            return [round(float(lo[0]), 3), round(float(c[1]), 3), round(float(c[2]), 3)]
    return None


if __name__ == "__main__":
    main()
