"""(pod, Isaac Lab app) L9 v2 spawn smoke for an R1 Pro / G1 profile (harvest.l9.robot9.V2): convert the prepared URDF
to USD (once), spawn it fixed with a table + a few blocks, hold the ready pose, render the head and one wrist camera
to PNG, and check (a) the lowest robot point vs the floor, (b) the sim TCP pose vs the cuRobo IK target of
ready_pose.py, (c) the finger joints at an opening from the width map.
usage: spawn_smoke9.py <profile> <ready.json> <out dir> [--arm right] [--surface 0.75] [--edge 0.30] [--width 0.06]"""
import argparse
import json
import math
import os

from isaaclab.app import AppLauncher

ap = argparse.ArgumentParser()
ap.add_argument("profile")
ap.add_argument("ready")
ap.add_argument("out")
ap.add_argument("--arm", default="right")
ap.add_argument("--surface", type=float, default=0.75)
ap.add_argument("--edge", type=float, default=0.30)
ap.add_argument("--width", type=float, default=0.06)
a = ap.parse_args()
app = AppLauncher(headless=True, enable_cameras=True).app

import numpy as np  # noqa: E402
import torch  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.assets import AssetBaseCfg, RigidObjectCfg  # noqa: E402
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg  # noqa: E402

from harvest.l9 import hcam9 as HC  # noqa: E402
from harvest.l9 import robot9 as R9  # noqa: E402


def main():
    os.makedirs(a.out, exist_ok=True)
    P = R9.V2[a.profile]
    ready = json.load(open(a.ready))
    r = ready[a.arm]
    init = R9.v2_init_joints(a.profile, a.arm, a.surface,
                             ready={a.arm: tuple(r["q"][j] for j in P["arms"][a.arm]["joints"])})
    init.update(R9.v2_width_to_joints(a.profile, a.arm, a.width))
    cams = ["cam_head", f"cam_wrist_{a.arm}"]
    cfg = InteractiveSceneCfg(num_envs=1, env_spacing=4.0)
    cfg.ground = AssetBaseCfg(prim_path="/World/ground", spawn=sim_utils.GroundPlaneCfg())
    cfg.light = AssetBaseCfg(prim_path="/World/light", spawn=sim_utils.DomeLightCfg(intensity=2500.0))
    cfg.robot = R9.v2_robot_cfg(a.profile, init)
    tz = a.surface
    cfg.table = AssetBaseCfg(prim_path="{ENV_REGEX_NS}/table", spawn=sim_utils.CuboidCfg(
        size=(0.60, 1.00, tz), visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.55, 0.42, 0.30)),
        collision_props=sim_utils.CollisionPropertiesCfg()),
        init_state=AssetBaseCfg.InitialStateCfg(pos=(a.edge + 0.30, 0.0, tz / 2)))
    cols = [(0.9, 0.2, 0.2), (0.2, 0.7, 0.2), (0.2, 0.3, 0.9)]
    for i, (dx, dy) in enumerate(((0.12, -0.20), (0.22, 0.0), (0.12, 0.20))):
        setattr(cfg, f"block{i}", RigidObjectCfg(prim_path=f"{{ENV_REGEX_NS}}/block{i}", spawn=sim_utils.CuboidCfg(
            size=(0.05, 0.05, 0.08), visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=cols[i]),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(), mass_props=sim_utils.MassPropertiesCfg(mass=0.1),
            collision_props=sim_utils.CollisionPropertiesCfg()),
            init_state=RigidObjectCfg.InitialStateCfg(pos=(a.edge + dx, dy, tz + 0.04))))
    for n, c in R9.v2_camera_cfgs(a.profile, cams).items():
        setattr(cfg, n, c)
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=0.01, device="cuda:0"))
    sim.set_camera_view((2.0, 2.0, 2.0), (0.0, 0.0, 0.8))
    scene = InteractiveScene(cfg)
    sim.reset()
    rob = scene["robot"]
    jn = rob.joint_names
    missing = [k for k in init if k not in jn]
    q0 = rob.data.default_joint_pos.clone()
    rob.set_joint_position_target(q0)
    for _ in range(int(os.environ.get("SMOKE_STEPS", "300"))):
        scene.write_data_to_sim()
        sim.step()
        scene.update(0.01)
    rep = {"profile": a.profile, "n_joints": len(jn), "n_bodies": len(rob.body_names), "init_missing": missing}
    # (a) lowest point
    from pxr import Usd, UsdGeom
    stage = sim.stage
    bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    rng = bb.ComputeWorldBound(stage.GetPrimAtPath("/World/envs/env_0/Robot")).ComputeAlignedRange()
    rep["robot_bbox_min_z"] = round(float(rng.GetMin()[2]), 4)
    rep["robot_bbox_max_z"] = round(float(rng.GetMax()[2]), 4)
    # (b) TCP vs the cuRobo target (target in the config base frame)
    r = ready[a.arm]
    bi, ti = rob.body_names.index(r["base_link"]), rob.body_names.index(r["tool_frame"])
    pb, qb = rob.data.body_pos_w[0, bi].cpu().numpy(), rob.data.body_quat_w[0, bi].cpu().numpy()
    pt, qt = rob.data.body_pos_w[0, ti].cpu().numpy(), rob.data.body_quat_w[0, ti].cpu().numpy()
    Rb = HC.quat_to_R(qb)
    rel = Rb.T @ (pt - pb)
    Rrel = Rb.T @ HC.quat_to_R(qt)
    rep["tcp_rel_base"] = rel.round(4).tolist()
    rep["tcp_err_mm"] = round(float(np.linalg.norm(rel - np.array(r["target_base"]))) * 1e3, 2)
    Rd = HC.quat_to_R(r.get("quat_base", (1.0, 0.0, 0.0, 0.0))).T @ Rrel
    rep["tcp_rot_err_deg"] = round(math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(Rd) - 1) / 2)))), 2)
    rep["base_world"] = pb.round(4).tolist()
    rep["tcp_world"] = pt.round(4).tolist()
    rep["tcp_above_surface_m"] = round(float(pt[2] - tz), 4)
    # (c) fingers
    fj = list(P["arms"][a.arm]["fingers"])
    fid = [jn.index(j) for j in fj]
    want = R9.v2_width_to_joints(a.profile, a.arm, a.width)
    got = rob.data.joint_pos[0, fid].cpu().numpy()
    rep["finger_err_max"] = round(float(np.max(np.abs(got - np.array([want[j] for j in fj])))), 4)
    arm_id = [jn.index(j) for j in P["arms"][a.arm]["joints"]]
    rep["arm_q_err"] = [round(float(v), 4) for v in (rob.data.joint_pos[0, arm_id] - q0[0, arm_id])]
    rep["arm_q_err_max"] = round(float((rob.data.joint_pos[0, arm_id] - q0[0, arm_id]).abs().max()), 4)
    body = [jn.index(j) for j in P["torso"]]
    rep["body_q_err"] = [round(float(v), 4) for v in (rob.data.joint_pos[0, body] - q0[0, body])]
    rep["tcp_quat_base"] = [round(float(v), 4) for v in HC.R_to_quat(Rrel)]
    from PIL import Image
    for n in cams:
        img = scene[n].data.output["rgb"][0].cpu().numpy()[..., :3].astype(np.uint8)
        Image.fromarray(img).save(os.path.join(a.out, f"{a.profile}_{n}.png"))
        rep[f"{n}_mean"] = round(float(img.mean()), 1)
    json.dump(rep, open(os.path.join(a.out, f"{a.profile}_smoke.json"), "w"), indent=1)
    print("SMOKE", json.dumps(rep), flush=True)


if __name__ == "__main__":
    try:
        main()
        c = 0
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        c = 1
    # no app.close(): it hangs in the kit shutdown (smoke 10-02); os._exit like tools/l9r
    os._exit(c)
