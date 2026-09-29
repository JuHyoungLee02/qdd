"""L8S change 28 (audit 4 item 7c): offline re-judge of finished episodes with the recorded truth, into a separate
file (the episode's meta / result stay as they are).
Rule: a failed into / onto episode whose target is a rolling object (clutter_x.ROLLING noun or sphericity >= 0.6) is a
success when, at the last call, the target is released (even number of hold changes) and its centre-bottom lies in
the container (oracle_state.container_contains with the container's layout yaw). Every other failed episode that
ends on a "done" row is listed as not re-judgeable: the recorded truth has positions only, no orientation.
usage: python rejudge_c28.py <collect root (.../train)> <out jsonl>"""
from __future__ import annotations

import glob
import json
import math
import os
import sys
from types import SimpleNamespace


def main(root: str, out: str) -> dict:
    from harvest.sim import objv as OV
    from harvest.sim.oracle_state import container_contains
    from harvest.teach_l8d.clutter_x import ROLLING, load_real
    rows_real = load_real()
    conts = OV.load_containers(usable_only=False)
    OV.register_containers({k: v for k, v in conts.items() if v.get("inside")})  # the ones with an opening box
    n = {"failed": 0, "now_success": 0, "done_row_not_rejudgeable": 0}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for m in sorted(glob.glob(os.path.join(root, "*", "*", "meta.json"))):
            d = os.path.dirname(m)
            meta = json.load(open(m))
            if meta.get("success"):
                continue
            n["failed"] += 1
            task = meta["task"]
            labs = [json.loads(x) for x in open(os.path.join(d, "labels.jsonl"))]
            done = bool(labs) and labs[-1].get("step") == "done"
            rec = {"episode": os.path.relpath(d, root), "task": task, "old_success": False, "new_success": False,
                   "last_step": labs[-1].get("step") if labs else None}
            if task.startswith("ov_into__") and labs:
                a, c = task[len("ov_into__"):].rsplit("__", 1)
                r = rows_real.get(a) or {}
                rolling = r.get("noun") in ROLLING or float(r.get("sphericity", 0.0)) >= 0.6
                res = json.load(open(os.path.join(d, "result.json")))
                released = len(res.get("hold_changes") or []) % 2 == 0
                if rolling:
                    sc = json.load(open(os.path.join(d, "scene.json")))
                    yaw = float(sc["layout"][c][2])
                    gt = labs[-1]["gt"]
                    b = SimpleNamespace(pos=gt["place"], quat_wxyz=[math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)])
                    bottom = float(gt["tgt"][2]) - float(r["height"]) / 2
                    inside = container_contains(c, b, gt["tgt"][:2], bottom)
                    rec.update(rolling=True, released=released, inside=bool(inside))
                    if inside and released:
                        rec.update(new_success=True, reason="rolling target released inside the container")
                        n["now_success"] += 1
            if done and not rec["new_success"]:
                rec["reason"] = "done row, not re-judgeable (no orientation in the recorded truth)"
                n["done_row_not_rejudgeable"] += 1
            f.write(json.dumps(rec) + "\n")
    return n


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1], sys.argv[2])))
