"""(pod, Isaac app headless) Joint limits as authored in a robot USD (what the PhysX articulation uses), in rad / m.
usage: run.sh lim .../usd_limits.py <usd> <out.json>"""
import json
import math
import sys

from isaacsim import SimulationApp

app = SimulationApp({"headless": True})
from pxr import Usd, UsdPhysics  # noqa: E402

stage = Usd.Stage.Open(sys.argv[1])
out = {}
for prim in stage.Traverse():
    if prim.IsA(UsdPhysics.RevoluteJoint):
        j = UsdPhysics.RevoluteJoint(prim)
        lo, hi = j.GetLowerLimitAttr().Get(), j.GetUpperLimitAttr().Get()
        if lo is not None and hi is not None:
            out[prim.GetName()] = {"type": "revolute", "lower": math.radians(lo), "upper": math.radians(hi),
                                   "path": str(prim.GetPath())}
    elif prim.IsA(UsdPhysics.PrismaticJoint):
        j = UsdPhysics.PrismaticJoint(prim)
        out[prim.GetName()] = {"type": "prismatic", "lower": j.GetLowerLimitAttr().Get(),
                               "upper": j.GetUpperLimitAttr().Get(), "path": str(prim.GetPath())}
json.dump(out, open(sys.argv[2], "w"), indent=1)
for k in sorted(out):
    if "arm" in k or "gripper" in k or "lift" in k or "head" in k:
        print(k, round(out[k]["lower"], 5), round(out[k]["upper"], 5))
app.close()
