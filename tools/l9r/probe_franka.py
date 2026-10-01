"""Franka profile probe (pod, Isaac, one GPU): build the env with the robot profile, print the articulation / prim
layout, TCP geometry, base pose and camera poses, step the arm to a top-down pose, save head / wrist renders.
usage (isaac.sh): harvest-free module path -> python -m tools.l9r.probe_franka <out dir>"""
import json
import os
import sys

import numpy as np


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    from harvest.l9 import robot9 as R9
    from harvest.sim.scene import make_env
    env = make_env(0, headless=True, cameras=R9.CAMERAS, depth=True, variant="drf", objset="x", robot="franka_mast")
    import omni.usd
    from pxr import Usd
    stage = omni.usd.get_context().get_stage()
    prims = [str(p.GetPath()) for p in Usd.PrimRange(stage.GetPrimAtPath("/World/envs/env_0/Robot"))
             if str(p.GetPath()).count("/") <= 6]
    rob = env.robot
    rep = {"bodies": list(rob.body_names), "joints": list(rob.joint_names), "prims": prims[:80],
           "tcp_offset": env.tcp_offset, "tip_offset": env.tip_offset, "fixed_base": bool(rob.is_fixed_base),
           "stiffness": rob.data.joint_stiffness[0].cpu().numpy().round(1).tolist(),
           "root": rob.data.root_pos_w[0].cpu().numpy().round(4).tolist()}
    env.reset()
    for _ in range(8):
        env.env.sim.render()
    from PIL import Image
    p, q = env.ee_pose()
    rep.update(ee_pos=np.round(p, 4).tolist(), ee_quat=np.round(q, 4).tolist(), width=env.gripper_width(),
               finger_mid=np.round(env.finger_mid(), 4).tolist())
    from harvest.sim.planner import OraclePlanner
    try:
        pl = OraclePlanner(env)
        rep["planner_tcp"] = np.round(pl.tcp_pose()[0], 4).tolist()
        goal = np.array([0.42, -0.23, env.table_top_z + 0.15])
        for i in range(160):
            qd = pl._ik(goal, np.array([0.7071, 0.0, 0.0, 0.7071]), 0.04)
            env.step(np.concatenate([qd, [0.08]]))
        rep["reach_err_mm"] = round(float(np.linalg.norm(pl.tcp_pose()[0] - goal)) * 1e3, 1)
        rep["ee_quat_after"] = np.round(env.ee_pose()[1], 4).tolist()
        for w in (0.08, 0.04, 0.0):
            for _ in range(20):
                env.step(np.concatenate([env.arm_q(), [w]]))
            rep[f"width_cmd_{w}"] = round(env.gripper_width(), 4)
    except Exception as ex:  # noqa: BLE001
        rep["planner_error"] = repr(ex)
    env.env.sim.render()
    for n in R9.CAMERAS:
        env.scene[n].update(0.0, force_recompute=True)
        Image.fromarray(env.camera_rgb(n)).save(os.path.join(out, f"{n}.png"))
        d = env.scene[n].data
        rep[f"{n}_K"] = d.intrinsic_matrices[0].cpu().numpy().round(2).tolist()
    json.dump(rep, open(os.path.join(out, "probe.json"), "w"), indent=1, default=str)
    print("PROBE " + json.dumps({k: rep[k] for k in rep if k not in ("prims", "bodies", "joints")}, default=str), flush=True)
    print("BODIES " + json.dumps(rep["bodies"]), flush=True)
    print("RUN_DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
        code = 0
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)
