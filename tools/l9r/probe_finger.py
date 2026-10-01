"""Franka finger probe (pod, Isaac): finger tracking at the start pose with nothing near the hand, then the same
after moving the hand over the table, and the finger links' world positions (which side is slow).
usage (isaac.sh): tools.l9r.probe_finger <out dir>"""
import json
import os
import sys

import numpy as np


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    from harvest.l9 import robot9 as R9
    from harvest.sim.scene import make_env
    cams = R9.CAMERAS if "cams" in sys.argv[2:] else ()
    var = "drf" if "drf" in sys.argv[2:] else "standard"
    env = make_env(0, headless=True, cameras=cams, depth=bool(cams), variant=var, objset="x", robot="franka_mast")
    env.reset()
    d = env.robot.data
    fid = [env.robot.joint_names.index(n) for n in R9.FINGERS]
    bid = [env.robot.body_names.index(b) for b in R9.FINGER_BODIES]
    rep = {}

    def trace(tag, widths, hold_q=None):
        t = []
        for i, w in enumerate(widths):
            q = env.arm_q() if hold_q is None else hold_q
            env.step(np.concatenate([q, [w]]))
            t.append([i, round(float(w), 3), d.joint_pos[0, fid].cpu().numpy().round(4).tolist(),
                      d.applied_torque[0, fid].cpu().numpy().round(1).tolist(),
                      d.body_pos_w[0, bid].cpu().numpy().round(3).tolist()])
        rep[tag] = t

    q0 = env.arm_q().copy()
    trace("start_close_open", [0.0] * 20 + [0.08] * 20, q0)
    trace("start_open_hold", [0.08] * 20, q0)
    from harvest.sim.planner import OraclePlanner
    pl = OraclePlanner(env)
    goal = np.array([0.42, -0.23, env.table_top_z + 0.15])
    for _ in range(160):
        env.step(np.concatenate([pl._ik(goal, np.array([0.7071, 0.0, 0.0, 0.7071]), 0.04), [0.08]]))
    rep["after_move"] = [d.joint_pos[0, fid].cpu().numpy().round(4).tolist(), d.applied_torque[0, fid].cpu().numpy().round(1).tolist()]
    q1 = env.arm_q().copy()
    trace("moved_close_open", [0.0] * 20 + [0.08] * 20, q1)
    json.dump(rep, open(os.path.join(out, "finger.json"), "w"))
    for k in ("start_close_open", "start_open_hold", "moved_close_open"):
        print(k, json.dumps([r[:4] for r in rep[k][::4]]), flush=True)
    print("after_move", rep["after_move"], flush=True)
    print("RUN_DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
        c = 0
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        c = 1
    os._exit(c)
