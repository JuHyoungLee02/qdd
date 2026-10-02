"""E-RC0 G1 geometry check (no model): base frame, TCP, head camera and depth of RcWorld against the sim.
Prints the robot0_base body pose, the eef site world position vs to_base, the env's robot0_base_to_eef_pos, the head
camera pose, the depth range, the median base-frame height of the depth points, the TCP projected into the head image,
and each object's sim position (base frame) vs the resolver xy at its projected pixel.
usage: geom_check.py <task>"""
import sys

import numpy as np

from harvest.astra_motion.geometry import pixel_of
from harvest.astra_solo import resolve as RS
from harvest.rc0.world import HEAD_CAM, HEAD_PX, RcWorld

RS.robot_mask = lambda hgt, plane, tcp: np.zeros(np.shape(hgt), bool)
w = RcWorld(sys.argv[1])
w.reset()
sim, raw = w.sim, w.raw
Rb, tb = w._base()
print("robot0_base body", np.round(tb, 3).tolist())
rob = raw.robots[0]
print("robot.base_pos", np.round(getattr(rob, "base_pos", np.zeros(3)), 3).tolist(), "root body", rob.robot_model.root_body)
sid = sim.model.site_name2id("gripper0_right_grip_site")
eef_w = np.array(sim.data.site_xpos[sid])
print("eef world", np.round(eef_w, 3).tolist(), "to_base", np.round(w.to_base(eef_w), 3).tolist(),
      "obs base_to_eef", np.round(w.obs["state.end_effector_position_relative"], 3).tolist())
o = w.observe(depth=True)
cam, d = o.cams["head"], o.depth["head"]
print("head cam t", np.round(cam.t, 3).tolist(), "fwd", np.round(cam.R[:, 2], 3).tolist(), "fx", round(cam.fx, 1))
print("depth range", float(np.nanmin(d)), float(np.nanmax(d)), "table_z", round(w.table_z, 3))
P = RS.depth_points(cam, d)
print("median point", np.round(np.nanmedian(P.reshape(-1, 3), 0), 3).tolist())
print("tcp pixel", pixel_of(cam, o.tcp))
for name, obj in list(getattr(raw, "objects", {}).items())[:6]:
    bid = sim.model.body_name2id(obj.root_body)
    pb = w.to_base(sim.data.body_xpos[bid])
    iu, iv, ins = pixel_of(cam, pb)
    r = RS.resolve_point(cam, d, w.table_z, [(iu + .5) / cam.W * 1000, (iv + .5) / cam.H * 1000], tcp=o.tcp) if ins else {}
    print(name, "base", np.round(pb, 3).tolist(), "px", (iu, iv, ins), "resolved", r.get("kind"), r.get("xy"), r.get("top"))
