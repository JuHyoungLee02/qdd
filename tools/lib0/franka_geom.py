"""E-LIB0b (prereg_lib0.md change 2): measure the Franka gripper facts the trained prompt states for the AI Worker,
in the robot base frame at the start pose (k = 0 of libero_spatial task 0): finger closing axis, pad length and
its extent around the TCP (grip_site), lowest gripper point below the TCP, gripper-body start above the TCP, open gap
and the gap after a close on nothing. usage: franka_geom.py"""
import json

import numpy as np

from harvest.lib0.world import LiberoWorld

w = LiberoWorld("libero_spatial", 0)
w.reset(0)
sim, m = w.sim, w.sim.model
Rb, tb = w._base()
tcp = w.status()["tcp"]


def zext(i):
    """(min z, max z) in the base frame of geom i (box / capsule / mesh via rbound for meshes)."""
    R = Rb.T @ np.array(sim.data.geom_xmat[i]).reshape(3, 3)
    c = Rb.T @ (np.array(sim.data.geom_xpos[i]) - tb)
    t, s = int(m.geom_type[i]), np.array(m.geom_size[i])
    if t == 6:  # box
        h = float(np.abs(R[2]) @ s)
    elif t in (3, 5):  # capsule / cylinder: radius + half length along local z
        h = float(s[0] + abs(R[2, 2]) * s[1]) if t == 3 else float(abs(R[2, 2]) * s[1] + s[0] * np.hypot(R[2, 0], R[2, 1]))
    else:
        h = float(m.geom_rbound[i])
    return c[2] - h, c[2] + h, c


out = {"tcp": np.round(tcp, 4).tolist(), "geoms": {}}
for i in range(m.ngeom):
    n = m.geom_id2name(i) or ""
    if n.startswith("gripper0_"):
        lo, hi, c = zext(i)
        out["geoms"][n] = {"type": int(m.geom_type[i]), "dz_lo_mm": round((lo - tcp[2]) * 1e3, 1),
                           "dz_hi_mm": round((hi - tcp[2]) * 1e3, 1), "c": np.round(c, 4).tolist()}
bl = [b for b in range(m.nbody) if "leftfinger" in (m.body_id2name(b) or "") or "finger1" in (m.body_id2name(b) or "")]
br = [b for b in range(m.nbody) if "rightfinger" in (m.body_id2name(b) or "") or "finger2" in (m.body_id2name(b) or "")]
if bl and br:
    d = Rb.T @ (np.array(sim.data.body_xpos[bl[0]]) - np.array(sim.data.body_xpos[br[0]]))
    out["finger_axis_base"] = np.round(d / np.linalg.norm(d), 3).tolist()
out["w_open_m"] = w.w_open
for _ in range(15):
    w.step(tcp + np.array([0, 0, 0.05]), w.w_open)
for _ in range(20):
    w.step(tcp + np.array([0, 0, 0.05]), 0.0)
out["gap_closed_on_nothing_m"] = round(w._gap(), 4)
print(json.dumps(out, indent=1))
