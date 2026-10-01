"""E-LIB0 setup probe (no model): build one LIBERO task env, start episode k=0 as openpi, print the controller /
frames / gripper facts and render the head camera (rgb + depth + robot segmentation) -> <out>/probe_*.png.
usage: probe_env.py <suite> <task> <out dir>"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image

from harvest.lib0.world import HEAD_CAM, HEAD_PX, LiberoWorld

suite, tid, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
os.makedirs(out, exist_ok=True)
t0 = time.time()
w = LiberoWorld(suite, tid)
t1 = time.time()
w.reset(0)
t2 = time.time()
rs = w.rs
c = rs.robots[0].controller
info = {"build_s": round(t1 - t0, 1), "reset_s": round(t2 - t1, 1), "language": w.task.language,
        "controller": type(c).__name__, "control_freq": rs.control_freq, "dt": w.dt, "horizon": rs.horizon,
        "ignore_done": getattr(rs, "ignore_done", None), "output_max": np.asarray(c.output_max).tolist(),
        "use_delta": getattr(c, "use_delta", None), "base": [np.round(x, 4).tolist() for x in w._base()],
        "tcp_base": np.round(w.status()["tcp"], 4).tolist(), "w_open": w.w_open, "table_z": round(w.table_z, 4),
        "ooi": w.objects_of_interest(), "objects": w.object_names(), "n_robot_geoms": len(w.robot_geoms),
        "ooi_pos": {k: (None if w.obj_pos(k) is None else np.round(w.obj_pos(k), 4).tolist()) for k in w.objects_of_interest()}}
print(json.dumps(info, indent=1))
t3 = time.time()
rgb, d, s = w.render(HEAD_CAM, HEAD_PX, HEAD_PX, depth=True, seg=True)
t4 = time.time()
print("render_head_s", round(t4 - t3, 3), "depth range", float(np.nanmin(d)), float(np.nanmax(d)), "robot px", int(s.sum()))
Image.fromarray(rgb).save(os.path.join(out, f"probe_{suite}_{tid}_head.png"))
Image.fromarray((s * 255).astype(np.uint8)).save(os.path.join(out, f"probe_{suite}_{tid}_seg.png"))
dd = np.clip((d - np.nanmin(d)) / (np.nanmax(d) - np.nanmin(d)) * 255, 0, 255).astype(np.uint8)
Image.fromarray(dd).save(os.path.join(out, f"probe_{suite}_{tid}_depth.png"))
# step timing: 40 control steps holding the pose
t5 = time.time()
for _ in range(40):
    w.step(w.status()["tcp"], w.w_open)
t6 = time.time()
print("step_s", round((t6 - t5) / 40, 4), "tcp after hold", np.round(w.status()["tcp"], 4).tolist(), "done", w.done)
# move test: +5 cm z over 40 steps with the reference ramp
p0 = np.asarray(w.status()["tcp"], float)
for i in range(40):
    w.step(p0 + np.array([0, 0, 0.05 * min(1.0, (i + 1) / 20)]), w.w_open)
print("after +5cm z", np.round(w.status()["tcp"] - p0, 4).tolist())
fr = w.frame()
Image.fromarray(np.concatenate([fr["head"], fr["wrist"]], 1)).save(os.path.join(out, f"probe_{suite}_{tid}_frame.png"))
print("PROBE_OK")
