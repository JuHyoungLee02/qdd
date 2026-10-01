"""E-LIB0 pre-run tool (no model; prereg change 1 + gate G1): over the 40 tasks (k = 0) record, in the robot base frame,
every BDDL object's position, the measured table height and the start TCP -> the workspace box to fix (all objects'
xy + margin, rounded out to 5 cm); and G1: each object-of-interest's sim position projected into the head camera ->
resolve.resolve_point on the head depth (robot pixels removed) -> xy error to the sim position (truth used only here).
Writes <out>/box_g1.json and the first frame of each suite with the TCP ring (<out>/g1_<suite>.png).
usage: box.py <out dir> [suites comma]"""
import json
import os
import sys

import numpy as np
from PIL import Image

from harvest.astra_motion.geometry import pixel_of
from harvest.astra_solo import nd as ND
from harvest.astra_solo import resolve as RS
from harvest.lib0.world import SUITES, LiberoWorld

RS.robot_mask = lambda hgt, plane, tcp: np.zeros(np.shape(hgt), bool)
out = sys.argv[1]
suites = sys.argv[2].split(",") if len(sys.argv) > 2 else list(SUITES)
os.makedirs(out, exist_ok=True)
rows = []
for s in suites:
    for tid in range(10):
        w = LiberoWorld(s, tid)
        w.reset(0)
        obs = w.observe(depth=True)
        cam, d = obs.cams["head"], obs.depth["head"]
        objs = {k: w.obj_pos(k) for k in w.object_names()}
        g1 = {}
        for k in w.objects_of_interest():
            p = objs.get(k)
            if p is None:
                continue
            iu, iv, ins = pixel_of(cam, p)
            if not ins:
                g1[k] = {"inside": False}
                continue
            r = RS.resolve_point(cam, d, w.table_z, [(iu + 0.5) / cam.W * 1000, (iv + 0.5) / cam.H * 1000],
                                 tcp=obs.tcp)
            err = None if r.get("xy") is None else round(float(np.linalg.norm(np.asarray(r["xy"]) - p[:2])) * 1e3, 1)
            g1[k] = {"kind": r["kind"], "xy_err_mm": err, "top": r.get("top"), "obj_z": round(float(p[2]), 4)}
        rows.append({"suite": s, "task": tid, "language": w.task.language, "table_z": round(w.table_z, 4),
                     "tcp0": np.round(obs.tcp, 4).tolist(), "w_open": round(w.w_open, 4),
                     "objs": {k: (None if v is None else np.round(v, 4).tolist()) for k, v in objs.items()}, "g1": g1})
        if tid == 0:
            ring, _ = ND.ring_overlay(obs.rgb["head"], cam, obs.tcp)
            Image.fromarray(ring).save(os.path.join(out, f"g1_{s}.png"))
        print(json.dumps({"suite": s, "task": tid, "table_z": rows[-1]["table_z"], "g1": g1}), flush=True)
        w.close()
xy = np.array([v[:2] for r in rows for v in r["objs"].values() if v is not None])
lo, hi = xy.min(0) - 0.05, xy.max(0) + 0.05
box = {"x": [float(np.floor(lo[0] * 20) / 20), float(np.ceil(hi[0] * 20) / 20)],
       "y": [float(np.floor(lo[1] * 20) / 20), float(np.ceil(hi[1] * 20) / 20)]}
errs = [g["xy_err_mm"] for r in rows for g in r["g1"].values() if g.get("xy_err_mm") is not None]
summ = {"box_from_objects": box, "obj_xy_min": xy.min(0).round(3).tolist(), "obj_xy_max": xy.max(0).round(3).tolist(),
        "table_z_range": [min(r["table_z"] for r in rows), max(r["table_z"] for r in rows)],
        "g1_xy_err_mm": {"n": len(errs), "median": float(np.median(errs)) if errs else None,
                         "p90": float(np.percentile(errs, 90)) if errs else None, "max": max(errs) if errs else None}}
json.dump({"summary": summ, "rows": rows}, open(os.path.join(out, "box_g1.json"), "w"), indent=1)
print("SUMMARY " + json.dumps(summ))
