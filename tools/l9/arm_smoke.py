"""L9 left-arm smoke (pod, Isaac): make_env(arm=...) on the L8 table, reset, report the robot prims / joint limits /
start TCP, drive the TCP to a few top-down targets with the arm's goal yaw (harvest.l9.arm.goal_yaw) and report the
reach error, the finger axis (world direction between the two finger pads) and the max joint step; saves head and
wrist PNGs. usage: python -m tools.l9.arm_smoke --arm left --out DIR"""
from __future__ import annotations

import argparse
import json
import os


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="left")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    code = 0
    try:
        import numpy as np

        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.l9 import arm as A
        from harvest.sim import scene as SC
        from harvest.sim.planner import OraclePlanner
        from harvest.teach_l8d.clutter_x import set_arm_inertia
        os.makedirs(a.out, exist_ok=True)
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER, arm=a.arm)
        import omni.usd
        from pxr import Usd
        stage = omni.usd.get_context().get_stage()
        root = stage.GetPrimAtPath("/World/envs/env_0/Robot/ffw_sg2_follower")
        kids = [c.GetName() for c in root.GetChildren()]
        lim = {}
        for p in Usd.PrimRange(stage.GetPrimAtPath("/World/envs/env_0/Robot")):
            if p.GetName().startswith(("arm_l_joint", "arm_r_joint")):
                lo, hi = p.GetAttribute("physics:lowerLimit"), p.GetAttribute("physics:upperLimit")
                if lo and lo.IsValid():
                    lim[p.GetName()] = [round(float(lo.Get()), 2), round(float(hi.Get()), 2)]
        env.reset()
        set_arm_inertia(env.robot, A.LEFT_HEAD_INERTIA)
        pl = OraclePlanner(env)
        tcp0 = [round(float(v), 4) for v in pl.tcp_pose()[0]]
        q0 = [round(float(v), 4) for v in env.arm_q()]
        res = {"arm": a.arm, "robot_children": kids, "limits": lim, "tcp0": tcp0, "q0": q0,
               "tcp_offset": env.tcp_offset, "targets": []}
        tz = float(env.table_top_z)
        s = A.side(a.arm)
        yaw = A.goal_yaw(a.arm, np.pi / 2)
        gq = np.array(A.yaw_quat(yaw))
        from harvest.sim.planner import W_MAX, _slerp_step
        from harvest.teach_l8d.clutter_x import ARM_DQ
        cq = np.asarray(pl.cmd_quat, float)
        qprev = env.robot.data.joint_pos[0].cpu().numpy().copy()
        maxdq = 0.0
        for k, (x, y, dz) in enumerate([(0.42, -0.20, 0.15), (0.50, -0.10, 0.10), (0.38, -0.30, 0.08)]):
            goal = np.array([x, s * y, tz + dz])
            for _ in range(160):
                cq = _slerp_step(cq, gq, W_MAX * env.step_dt)
                q = pl._ik(goal, cq, ARM_DQ)
                env.step(np.concatenate([q, [SC.GRIP_MAX_W]]).astype(np.float32))
                qn = env.robot.data.joint_pos[0].cpu().numpy().copy()
                ids = env.arm_ids
                maxdq = max(maxdq, float(np.abs(qn[ids] - qprev[ids]).max()))
                qprev = qn
            p, qe = pl.tcp_pose()
            f = env.robot.data.body_pos_w[0, env.finger_idx[1]].cpu().numpy() - \
                env.robot.data.body_pos_w[0, env.finger_idx[3]].cpu().numpy()
            f = f / (np.linalg.norm(f) + 1e-9)
            res["targets"].append({"goal": [round(float(v), 3) for v in goal], "err_mm": round(float(np.linalg.norm(p - goal)) * 1000, 1),
                                   "finger_axis": [round(float(v), 2) for v in f], "q": [round(float(v), 3) for v in env.arm_q()]})
            env.env.sim.render()
            for n in CAMS:
                env.scene[n].update(0.0, force_recompute=True)
            from PIL import Image
            for n in ("cam_head", A.wrist_camera(a.arm)):
                Image.fromarray(env.camera_rgb(n)[..., :3]).save(os.path.join(a.out, f"{a.arm}_{k}_{n}.png"))
        res["max_dq_arm"] = round(maxdq, 4)
        json.dump(res, open(os.path.join(a.out, f"smoke_{a.arm}.json"), "w"), indent=1)
        print("SMOKE " + json.dumps(res), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
