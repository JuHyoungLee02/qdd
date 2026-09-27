"""E-DIST8 point-failure diagnosis (D / H point answers): for each approach / carry state of an evaluation set, where
the model's point lands after the runtime depth resolution — on the intended object, on another object (which), on
the table, or nothing — and the pixel error to the label point; grouped by the intended object key.
usage: python dist8_pointdiag.py <data jsonl> <eval dir> <arm pt|h>   -> one JSON line"""
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

from harvest.astra_motion.geometry import Cam
from harvest.astra_solo import resolve as RS
from harvest.teach_pt import metrics as M

data, ev, arm = sys.argv[1:4]
rows = {json.loads(x)["id"]: json.loads(x) for x in open(data, encoding="utf-8")}
reps = {json.loads(x)["id"]: json.loads(x) for x in open(os.path.join(ev, "replies.jsonl"))}
land, by_obj, px = Counter(), defaultdict(Counter), []
for i, r in rows.items():
    if r["kind"] != "control" or r["step"] not in M.APPROACH_STEPS + M.CARRY_STEPS or i not in reps:
        continue
    p, _ = M.validate(reps[i]["text"], arm)
    if p is None or p["command"].get("point_2d") is None:
        land["no_point"] += 1
        continue
    want = r["tgt"] if r["step"] in M.APPROACH_STEPS else r["place"]
    cam = Cam.from_json(json.load(open(r["cams_path"]))["head"])
    if not r.get("depth_path"):
        land["no_depth"] += 1
        continue
    res = RS.resolve_point(cam, np.load(r["depth_path"])["depth"], r["pt_state"]["plane"], p["command"]["point_2d"],
                           tcp=r["gt"]["tcp"])
    objs = {r["tgt"]: r["gt"]["tgt"], r["place"]: r["gt"]["place"], **r["gt"]["others"]}
    if res["kind"] != "object":
        where = res["kind"]
    else:
        k, d = min(((k, np.hypot(res["xy"][0] - c[0], res["xy"][1] - c[1])) for k, c in objs.items()), key=lambda t: t[1])
        where = ("intended" if k == want else "other:" + k) if d < 0.05 else "object_far"
    land[where.split(":")[0]] += 1
    by_obj[want][where] += 1
    lab = json.loads(r["answer"])["command"]
    if lab.get("point_2d"):
        px.append(float(np.hypot((p["command"]["point_2d"][0] - lab["point_2d"][0]) * cam.W / 1000,
                                 (p["command"]["point_2d"][1] - lab["point_2d"][1]) * cam.H / 1000)))
print(json.dumps({"data": data, "eval": ev, "landing": land, "point_px_median": round(float(np.median(px)), 1) if px else None,
                  "by_intended": {k: dict(v) for k, v in sorted(by_obj.items())}}))
