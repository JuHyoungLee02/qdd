"""E-PT label check (gate G0 diagnostics): for every labelled call of the episodes under <root>, print the step, the
pt label verdict and, for point steps, what the depth resolver returns at the projected top centre / body centre of the
intended object (kind, footprint-centre xy error, top error, region size, plane vs the true table).
usage: python inspect_rows.py <episode dir or root> [table_z]"""
import glob
import json
import os
import sys

import numpy as np

from harvest.astra_motion import geometry as G
from harvest.astra_motion.harness import obj_height
from harvest.astra_solo import resolve as RS
from harvest.astra_solo.pt_truth import STEP_MAP

root = sys.argv[1]
tz = float(sys.argv[2]) if len(sys.argv) > 2 else 0.85
for lab in sorted(glob.glob(os.path.join(root, "**", "labels.jsonl"), recursive=True)):
    ep = os.path.dirname(lab)
    for line in open(lab):
        r = json.loads(line)
        out = {"ep": os.path.relpath(ep, root), "call": r["call"], "step": r.get("step"),
               "pt": r.get("pt_answer") is not None, "meta": r.get("pt_meta")}
        if r.get("step") in STEP_MAP and STEP_MAP[r["step"]][0]:
            d = os.path.join(ep, "calls", f"c{r['call']:03d}")
            cam = G.Cam.from_json(json.load(open(os.path.join(d, "cams.json")))["head"])
            depth = np.load(os.path.join(d, "head_depth.npz"))["depth"]
            key = r[STEP_MAP[r["step"]][0]]
            c = np.asarray(r["gt"]["tgt" if key == r["tgt"] else "place"], float)
            top = c[2] + obj_height(key) / 2
            for name, p in (("top", [c[0], c[1], top]), ("body", c)):
                u, v, z = G.project(cam, p)
                res = RS.resolve_point(cam, depth, tz, RS.to_scaled(u, v, cam.W, cam.H))
                e = None if res["xy"] is None else round(float(np.hypot(res["xy"][0] - c[0], res["xy"][1] - c[1])) * 1e3, 1)
                out[name] = {"uv": [round(u), round(v)], "kind": res["kind"], "xy_mm": e,
                             "top_mm": None if res["top"] is None else round((res["top"] - top) * 1e3, 1),
                             "n_px": res["n_px"], "plane_mm": round((res["plane"] - tz) * 1e3, 1)}
            fin = depth[np.isfinite(depth)]
            out["depth"] = [round(float(fin.min()), 3), round(float(np.median(fin)), 3)] if fin.size else None
        print(json.dumps(out))
