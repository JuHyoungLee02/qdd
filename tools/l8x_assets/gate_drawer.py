"""Drawer gate (prereg_l8x_tasks 2.4 / change 6; pod Isaac, outside the L8-D runner): clean truth episodes of
dr__<piece>__<handle> on one articulated THOR piece per process.

The piece (original articulated USD, fixed root, drawer joints kept, drawer links 1 kg, damped) stands on the floor
facing the robot (Y-up fix + yaw -90 deg); after a provisional reset it is moved so the chosen handle's centre is at
(HANDLE_X, HANDLE_Y) and its bottom on the floor, and the lift is set so the handle sits in the reach band
(teach_l8d.xdrawer / L8-D lift rule). Each episode: hard reset (drawers closed), then the truth plan
(xdrawer.plan_drawer) drives the arm through the OraclePlanner IK (5 mm per tick, as tools/l8x_assets/validate.py),
up to MAX_CALLS commands; judge xdrawer.success_drawer. Head-camera frames -> mp4 per episode.
usage: python -m tools.l8x_assets.gate_drawer --piece-usd U --piece NAME --tasks t1,t2 --seeds s1,s2 --out DIR"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

HANDLE_X, HANDLE_Y = 0.50, -0.22
REL_Z = 0.95  # handle height relative to the default-lift reach band centre
MAX_CALLS = 60
STEP_M = 0.005
HOLD = 10
CLEAR_DZ = 0.08


def joints_all(usd: str) -> list:
    from pxr import Usd
    st = Usd.Stage.Open(usd)
    out = []
    for p in st.Traverse():
        t = p.GetTypeName()
        if "Joint" in t:
            b0 = p.GetRelationship("physics:body0").GetTargets()
            b1 = p.GetRelationship("physics:body1").GetTargets()
            out.append({"name": p.GetName(), "type": t, "b0": str(b0[0].name) if b0 else None,
                        "b1": str(b1[0].name) if b1 else None})
    return out


def drawer_joint_of(joints: list, handle: str):
    """The prismatic joint that moves the handle: the handle body is fixed-jointed to a drawer body (or is it)."""
    bodies = {handle}
    for j in joints:
        if j["type"] == "PhysicsFixedJoint" and handle in (j["b0"], j["b1"]):
            bodies.add(j["b1"] if j["b0"] == handle else j["b0"])
    for j in joints:
        if j["type"] == "PhysicsPrismaticJoint" and (j["b0"] in bodies or j["b1"] in bodies):
            return j["name"]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--piece-usd", required=True)
    ap.add_argument("--piece", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--diag", action="store_true", help="per-command reach / joint-limit lines + wrist frames")
    ap.add_argument("--max-calls", type=int, default=MAX_CALLS)
    ap.add_argument("--approach", choices=("top", "front"), default="top", help="change 10: front grasp")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import scene as SC
        from harvest.teach_l8d import xdrawer as XD
        from tools.l8x_assets.validate import _save, _video
        tasks, seeds = a.tasks.split(","), [int(s) for s in a.seeds.split(",")]
        orig = SC._build_cfg
        q0 = (0.7071068, 0.7071068, 0.0, 0.0)  # Y-up -> Z-up
        qz = (math.cos(-math.pi / 4), 0.0, 0.0, math.sin(-math.pi / 4))  # yaw -90: the front faces the robot (-x)
        from harvest.sim.objv import qmul
        rot = qmul(qz, q0)

        def patched(*x, **k):
            import isaaclab.sim as sim_utils
            from isaaclab.actuators import ImplicitActuatorCfg
            from isaaclab.assets import ArticulationCfg
            cfg, layout = orig(*x, **k)
            cfg.scene.table = None
            cfg.scene.art = ArticulationCfg(
                prim_path="{ENV_REGEX_NS}/ART",
                spawn=sim_utils.UsdFileCfg(
                    usd_path=a.piece_usd, mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
                    articulation_props=sim_utils.ArticulationRootPropertiesCfg(fix_root_link=True)),
                init_state=ArticulationCfg.InitialStateCfg(pos=(1.2, 0.0, 0.0), rot=rot),
                actuators={"drawers": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=0.0, damping=20.0)})
            return cfg, layout

        SC._build_cfg = patched
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER)
        joints = joints_all(a.piece_usd)
        env.layout = {}
        SC._LAYOUT["layout"] = {}
        for k in ("o3", "o5", "o8", "o9", "o10"):
            SC._LAYOUT["layout"].pop(k, None)
        env.reset(settle_s=0.2)
        art = env.scene["art"]
        bn, jn = list(art.body_names), list(art.joint_names)
        import omni.usd
        from pxr import Usd, UsdGeom
        stage = omni.usd.get_context().get_stage()

        def world_bbox(name=None):
            root = stage.GetPrimAtPath("/World/envs/env_0/ART")
            prim = root
            if name:
                for p in Usd.PrimRange(root):
                    if p.GetName() == name:
                        prim = p
                        break
            r = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(prim)
            rg = r.ComputeAlignedRange()
            return np.array(rg.GetMin()), np.array(rg.GetMax())

        def bar_bbox(handle):
            """change 8: the grasp bar = the handle body's longest collider (the body bbox also holds the mounting
            posts, which moved the centre ~1.4 cm towards the drawer front, under the top's overhang)."""
            root = stage.GetPrimAtPath("/World/envs/env_0/ART")
            hp = next((p for p in Usd.PrimRange(root) if p.GetName() == handle), None)
            cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy", "guide"])
            best = None
            for p in Usd.PrimRange(hp) if hp else []:
                if "Collider" not in p.GetName():
                    continue
                rg = cache.ComputeWorldBound(p).ComputeAlignedRange()
                if rg.IsEmpty():
                    continue
                lo_, hi_b = np.array(rg.GetMin()), np.array(rg.GetMax())
                if best is None or (hi_b - lo_).max() > (best[1] - best[0]).max():
                    best = (lo_, hi_b)
            return best if best is not None else world_bbox(handle)

        res = {}
        os.makedirs(a.out, exist_ok=True)
        placed = None
        for task, seed in zip(tasks, seeds):
            handle = task.split("__")[2]
            jname = drawer_joint_of(joints, handle)
            r = {"task": task, "seed": seed, "joint": jname}
            if jname is None or handle not in bn or jname not in jn:
                r.update(success=False, reason=f"handle/joint not found ({jname})")
                res[str(seed)] = r
                print("DR " + json.dumps(r), flush=True)
                continue
            hi_ = bn.index(handle)
            if placed != handle:  # move the piece: handle centre at (HANDLE_X, HANDLE_Y), bottom on the floor
                if placed is not None:  # USD poses are only consistent with physics before the first move
                    raise RuntimeError("one handle per process (the USD bbox goes stale after a root move)")
                lo, hi = bar_bbox(handle)
                hc = (lo + hi) / 2
                print("DR_BAR", handle, [round(float(v), 3) for v in lo], [round(float(v), 3) for v in hi], flush=True)
                # the handle bar centre in the handle body's frame (physics pose and USD agree before any move)
                bq = art.data.body_quat_w[0, hi_].cpu().numpy()
                from harvest.sim.objv import qinv, qrot
                hoff_local = qrot(qinv(tuple(bq)), hc - art.data.body_pos_w[0, hi_].cpu().numpy())
                plo, phi = world_bbox()
                dpos = np.array([HANDLE_X - hc[0], HANDLE_Y - hc[1], -plo[2]])
                p0 = art.data.default_root_state[0, :3].cpu().numpy()
                newp = p0 + dpos
                art.data.default_root_state[0, :3] = env.torch.tensor(newp, device=env.env.device)
                art.cfg.init_state.pos = tuple(float(v) for v in newp)
                hz = float(hc[2] + dpos[2])
                clear_z = float(phi[2] + dpos[2] + CLEAR_DZ)  # change 7: approach above the piece top
                lift = float(np.clip(SC.INIT_JOINTS["lift_joint"] + (hz - REL_Z), -0.5, 0.0))
                li = env.robot.joint_names.index("lift_joint")
                env.robot.cfg.init_state.joint_pos["lift_joint"] = lift
                env.robot.data.default_joint_pos[0, li] = lift
                placed = handle
            env.reset(settle_s=0.5)
            ji = jn.index(jname)
            from harvest.sim.planner import MAX_DQ_RAD, W_MAX, OraclePlanner, _slerp_step
            pl = OraclePlanner(env)
            plan = XD.plan_drawer
            if a.approach == "front":  # gripper axis +x (towards the piece), fingers closing vertically
                pl.goal_quat = np.asarray(qmul((math.cos(-math.pi / 4), 0.0, math.sin(-math.pi / 4), 0.0),
                                               (math.cos(math.pi / 4), 0.0, 0.0, math.sin(math.pi / 4))), float)
                plan = XD.plan_drawer_front
            cmd_q = np.asarray(pl.cmd_quat, float)
            w_cmd = float(SC.GRIP_MAX_W)
            frames = []
            root0 = art.data.root_pos_w[0].cpu().numpy().copy()

            def status():
                return {"tcp": np.asarray(pl.tcp_pose()[0], float), "grip_w": float(env.gripper_width()),
                        "handle": art.data.body_pos_w[0, hi_].cpu().numpy()
                        + qrot(tuple(art.data.body_quat_w[0, hi_].cpu().numpy()), hoff_local),
                        "joint": float(art.data.joint_pos[0, ji])}

            def tick(p):
                nonlocal cmd_q
                cmd_q = _slerp_step(cmd_q, pl.goal_quat, W_MAX * env.step_dt)
                q = pl._ik(np.asarray(p, float), cmd_q, MAX_DQ_RAD)
                env.step(np.concatenate([q, [w_cmd]]).astype(np.float32))

            upper = float(art.data.soft_joint_pos_limits[0, ji, 1])  # change 11: shallow drawers (0.17 m travel)
            open_target = min(XD.OPEN_TARGET, round(0.9 * upper, 3))
            info = {"pull_dir": [-1.0, 0.0, 0.0], "open_target": open_target, "clear_z": clear_z}
            steps = []
            h_start = status()["handle"]
            for call in range(a.max_calls):
                st = status()
                step, cmd = plan(st, info, float(SC.GRIP_MAX_W))
                steps.append(step)
                if cmd["mode"] == "stop":
                    break
                if cmd.get("gripper") == "close":
                    w_cmd = 0.0
                elif cmd.get("gripper") == "open":
                    w_cmd = float(cmd.get("width_m", SC.GRIP_MAX_W))
                if cmd["mode"] == "eef":
                    tgt = np.asarray(cmd["position_m"], float)
                    cur = st["tcp"]
                    n = max(1, int(np.ceil(np.linalg.norm(tgt - cur) / STEP_M)))
                    for j in range(1, n + 1):
                        tick(cur + (tgt - cur) * j / n)
                        if j % 4 == 0:
                            env.env.sim.render()
                            env.scene["cam_head"].update(0.0, force_recompute=True)
                            frames.append(env.camera_rgb("cam_head").copy())
                    for _ in range(HOLD):
                        tick(tgt)
                    if a.diag:  # stall diagnosis: reached vs target, arm joints near limits
                        jp = env.robot.data.joint_pos[0].cpu().numpy()
                        lim = env.robot.data.soft_joint_pos_limits[0].cpu().numpy()
                        near_lim = [f"{n}:{jp[i]:.2f}[{lim[i, 0]:.2f},{lim[i, 1]:.2f}]"
                                    for i, n in enumerate(env.robot.joint_names)
                                    if min(jp[i] - lim[i, 0], lim[i, 1] - jp[i]) < 0.05]
                        env.env.sim.render()
                        env.scene["cam_wrist_right"].update(0.0, force_recompute=True)
                        _save(env.camera_rgb("cam_wrist_right").copy(),
                              os.path.join(a.out, f"diag_{seed}_{call:02d}_{step}.png"))
                        if call <= 3:  # gripper bodies (world) -> finger closing axis and housing size
                            bpos = env.robot.data.body_pos_w[0].cpu().numpy()
                            print("DR_BODIES", call, {n: [round(float(v), 3) for v in bpos[i]]
                                                      for i, n in enumerate(env.robot.body_names)
                                                      if "gripper_r" in n or n.startswith("arm_r_link")}, flush=True)
                        print("DR_DIAG", call, step, "tgt", [round(float(v), 3) for v in tgt], "tcp",
                              [round(float(v), 3) for v in status()["tcp"]], "w", round(float(env.gripper_width()), 4),
                              "lim", near_lim, flush=True)
                else:
                    for _ in range(15):
                        tick(st["tcp"])
            st = status()
            move = float(np.linalg.norm(art.data.root_pos_w[0].cpu().numpy() - root0))
            ok = XD.success_drawer(st["joint"], st["grip_w"], float(SC.GRIP_MAX_W), move, open_target)
            r.update(success=bool(ok), open_target=open_target, joint_end=round(st["joint"], 4),
                     grip_end=round(st["grip_w"], 4),
                     handle_start=[round(float(v), 3) for v in h_start], tcp_end=[round(float(v), 3) for v in st["tcp"]],
                     root_move_m=round(move, 4), n_calls=len(steps), steps=steps,
                     lift=round(float(env.robot.data.joint_pos[0, env.robot.joint_names.index("lift_joint")]), 4))
            res[str(seed)] = r
            tag = f"{task}_s{seed}"
            if frames:
                _video(frames, os.path.join(a.out, tag + ".mp4"))
                _save(frames[-1], os.path.join(a.out, tag + ".png"))
            print("DR " + json.dumps({k: v for k, v in r.items() if k != "steps"}), flush=True)
        with open(os.path.join(a.out, f"gate_{a.piece}.json"), "w") as f:
            json.dump(res, f, indent=1)
        print("DR_DONE", sum(v.get("success", False) for v in res.values()), "/", len(res), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
