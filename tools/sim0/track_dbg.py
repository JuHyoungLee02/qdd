"""E-SIM0 setup debug: EE tracking of the standard Google Robot controller (no model). Holds the start orientation
(rot=keep) or the straight-down one (rot=down) and steps toward a target 10 cm away; prints the TCP error per step."""
import sys

import numpy as np

from harvest.sim0.world import SimWorld, episodes, ep_name

mode = sys.argv[1]
e = [x for x in episodes() if ep_name(x) == "coke_upright_x0y0"][0]
w = SimWorld(e)
w.reset()
Rc, t0 = w.tcp_Rt()
if mode == "keep":
    w.R_goal = Rc
u = w.env.unwrapped
print("ee link", u.agent.controller.controllers["arm"].ee_link.name if hasattr(u.agent.controller, "controllers") else "?")
can = w.to_base(u.obj.pose.p)
goal = np.array([can[0], can[1], t0[2]])
print("start", np.round(t0, 3), "goal", np.round(goal, 3))
for k in range(12):
    w.step(goal, w.w_open)
    Rn, tn = w.tcp_Rt()
    ang = np.degrees(np.linalg.norm(__import__("harvest.sim0.world", fromlist=["rotvec"]).rotvec(w.R_goal @ Rn.T)))
    print(k, np.round(tn, 3), "err mm", round(float(np.linalg.norm(tn - goal)) * 1e3, 1), "rot err deg", round(float(ang), 1))
