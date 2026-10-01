"""L9 v2 Planner9 API smoke on the bundled cuRobo franka.yml (no Isaac): world update, batched IK, plan_grasp with a
+z standoff, plan_pose with an attached box, resample bound. Run with the Isaac python + /data/harvest/l9v2/pylib."""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import plan9 as P  # noqa: E402
from harvest.l9.grasp9 import frame_of  # noqa: E402


def main():
    robot = sys.argv[1] if len(sys.argv) > 1 else "franka.yml"
    t0 = time.time()
    pl = P.Planner9(robot)
    print("init", round(time.time() - t0, 1), "s cuRobo", pl.version, pl.joint_names)
    parts = [{"id": "table", "prim": "cuboid", "pos": [0.5, 0.0, -0.02], "size": [0.6, 0.8, 0.04], "yaw": 0.0}]
    boxes = {"obj": ([0.45, 0.1, 0.05], [0.05, 0.05, 0.10], [1, 0, 0, 0])}
    pl.world(P.scene_cuboids(parts, boxes, np.eye(4)))
    q0 = pl.mp.default_joint_state.position.cpu().numpy().reshape(-1)[: len(pl.joint_names)]
    # franka tool z points along the fingers: approach a = +z_tool; a top grasp has z_tool = down
    Ts = []
    for a in (np.array([0, 0, -1.0]), np.array([0.7, 0, -0.7]), np.array([1.0, 0, 0.0])):
        R = frame_of(a, [0, 1.0, 0])
        R = R @ np.diag([1.0, -1.0, -1.0])  # G (z = -a) -> franka hand (z = +a)
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = R, [0.45, 0.1, 0.06]
        Ts.append(T)
    t0 = time.time()
    ok, q, margin = pl.ik(np.array(Ts))
    print("ik", ok, np.round(margin, 3), round(time.time() - t0, 2), "s")
    for T, name in zip(Ts, ("top", "oblique", "front")):
        t0 = time.time()
        r = pl.grasp(q0, T, standoff=-0.10, lift_dz=0.04)  # franka: pre-grasp is -z_tool
        n = {k: (None if r[k] is None else len(r[k])) for k in ("approach", "grasp", "lift")}
        print("grasp", name, r["ok"], r["status"], n, round(time.time() - t0, 2), "s")
        if r["ok"]:
            Q = np.concatenate([r["approach"], r["grasp"], r["lift"]])
            out = P.resample(Q)
            print("  resampled", len(Q), "->", len(out), "max step", round(P.max_step(out), 4))
            qe = r["lift"][-1]
            pl.attach(qe, ["obj"])
            T2 = np.eye(4)
            T2[:3, :3], T2[:3, 3] = T[:3, :3], [0.4, -0.2, 0.25]
            t0 = time.time()
            Qc = pl.pose(qe, T2)
            print("  carry attached", None if Qc is None else len(Qc), round(time.time() - t0, 2), "s")
            pl.detach()
    print("SMOKE_DONE")


if __name__ == "__main__":
    main()
