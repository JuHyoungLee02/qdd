"""Place accuracy of L9 v2 episodes (pure): for every lower_open call, the label put TCP, the TCP at that call, the
object and place centres at that call and at the episode end (labels 'gt'), mm offsets.
usage: python tools/l9/v2_place_check.py <collect root> [--since EPOCH] [--n 12]"""
import glob
import json
import os
import sys

import numpy as np

a = sys.argv[1:]
since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
nmax = int(a[a.index("--n") + 1]) if "--n" in a else 12
k = 0
for m in sorted(glob.glob(os.path.join(a[0], "**", "meta.json"), recursive=True)):
    if os.path.getmtime(m) < since:
        continue
    meta = json.load(open(m))
    if meta.get("grasp_v2") is None or meta["success"]:
        continue
    d = os.path.dirname(m)
    rows = [json.loads(x) for x in open(os.path.join(d, "labels.jsonl"))]
    lo = [r for r in rows if r.get("step") == "lower_open"]
    if not lo:
        continue
    r0, rl = lo[0], rows[-1]
    cmd = json.loads(r0["answer"])["command"]["position_m"]
    g0, gl = r0["gt"], rl["gt"]
    put = np.array(cmd)
    print(os.path.relpath(d, a[0]), meta.get("task_id"), "end", meta.get("end_reason"))
    print("   put TCP", np.round(put, 3).tolist(), "tcp@call", np.round(g0["tcp"], 3).tolist(),
          "obj@call", np.round(g0["tgt"], 3).tolist(), "place", np.round(g0["place"], 3).tolist())
    off_call = 1000 * np.hypot(*(np.subtract(g0["tgt"][:2], g0["place"][:2])))
    off_end = 1000 * np.hypot(*(np.subtract(gl["tgt"][:2], gl["place"][:2])))
    print(f"   obj-place xy @lower_open call {off_call:.0f} mm, @end {off_end:.0f} mm, obj z end {gl['tgt'][2]:.3f}"
          f" place z {gl['place'][2]:.3f}, last step {rl.get('step')}")
    k += 1
    if k >= nmax:
        break
