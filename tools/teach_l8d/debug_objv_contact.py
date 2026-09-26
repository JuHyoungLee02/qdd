"""Debug (pod, Isaac): does an L8-X mesh object report contacts with the tray? Registers one object, builds the env with
objset x, puts the object on the tray, settles, prints the force matrices of the object's and the tray's sensors,
the oracle contacts / support and the predicates. usage: python -m tools.teach_l8d.debug_objv_contact <objv id>"""
import json
import os
import sys

import numpy as np


def main():
    code = 0
    try:
        from harvest.astra_motion.world_isaac import CAMS, NO_RENDER
        from harvest.sim import objv as OV
        from harvest.sim import scene as SC
        from harvest.sim.oracle_state import oracle_objects
        k = sys.argv[1]
        OV.register_for_tasks([f"ov_tray__{k}"])
        env = SC.make_env(0, headless=True, cameras=CAMS, depth=False, render_interval=NO_RENDER, objset="x",
                          task=f"ov_tray__{k}")
        env.set_seed(35070, f"ov_tray__{k}")
        env.reset()
        p5, _ = env.object_pose("o5")
        g = SC.OBJ_GEOM[k]
        hold = np.concatenate([env.arm_q(), [SC.GRIP_MAX_W]])
        c = np.array([p5[0], p5[1], p5[2] + 0.0075 + g["height"] / 2 + 0.002])
        r, q = OV.root_from_canonical(g, c, (1.0, 0.0, 0.0, 0.0))
        t = env.torch
        env.objects[k].write_root_pose_to_sim(t.tensor([[*r, *q]], dtype=t.float32, device=env.env.device))
        env.objects[k].write_root_velocity_to_sim(t.zeros((1, 6), device=env.env.device))
        for _ in range(40):
            env.step(hold)
        print("POSE", k, env.object_pose(k)[0].round(4).tolist(), "tray", p5.round(4).tolist(), flush=True)
        for j in (k, "o5"):
            fm = env.contact[j].data.force_matrix_w
            print("FM", j, None if fm is None else fm[0, 0].norm(dim=-1).cpu().numpy().round(3).tolist(), flush=True)
            print("NET", j, env.contact[j].data.net_forces_w[0].norm(dim=-1).cpu().numpy().round(3).tolist(), flush=True)
        objs, grip, contacts, support = oracle_objects(env)
        print("CONTACTS", sorted(tuple(sorted(c)) for c in contacts), "SUPPORT", support.get(k), flush=True)
        print("BODY", env.contact[k].body_names if hasattr(env.contact[k], "body_names") else None, flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
