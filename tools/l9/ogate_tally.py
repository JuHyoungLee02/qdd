"""L9 object gate tally: clean gate_move episodes per target (meta plan_row.fixed.A); pass = every try succeeded with
no arm jump (> 0.04 rad) when tried >= 2 times, fail = no success. usage: python ogate_tally.py <collect root> <out.json>"""
import glob
import json
import os
import sys

root, out = sys.argv[1], sys.argv[2]
per = {}
for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
    meta = json.load(open(m))
    row = meta.get("plan_row") or {}
    if row.get("def") != "gate_move":
        continue
    k = (row.get("fixed") or {}).get("A")
    d = per.setdefault(k, {"n": 0, "ok": 0})
    d["n"] += 1
    d["ok"] += int(bool(meta.get("success")) and (meta.get("max_dq_rad") or 0) <= 0.04)
for m in glob.glob(os.path.join(root, "**", "skipped.json"), recursive=True):
    row = json.load(open(m)).get("row") or {}
    k = (row.get("fixed") or {}).get("A")
    if k:
        per.setdefault(k, {"n": 0, "ok": 0})["skipped"] = per.get(k, {}).get("skipped", 0) + 1
ok = sorted(k for k, d in per.items() if d["n"] >= 2 and d["ok"] >= 2)
bad = sorted(k for k, d in per.items() if d["n"] >= 1 and d["ok"] == 0)
json.dump({"pass": ok, "fail": bad, "per": per}, open(out, "w"))
print(json.dumps({"objects": len(per), "pass": len(ok), "fail": len(bad),
                  "episodes": sum(d["n"] for d in per.values())}))
