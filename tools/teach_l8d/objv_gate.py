"""Objaverse object gate tally (prereg_l8d change 7): clean truth success per ov_* object in <root>/gate/*/*/meta.json;
pass = >= 2 of 3. usage: python objv_gate.py <gate collect root> <out.json>"""
import glob
import json
import os
import sys

root, out = sys.argv[1], sys.argv[2]
per = {}
for m in glob.glob(os.path.join(root, "gate", "*", "*", "meta.json")):
    m = json.load(open(m))
    t = str(m.get("task", ""))
    if not t.startswith("ov_") or m.get("style") != "clean":
        continue
    oid = t.split("__", 1)[1]
    d = per.setdefault(oid, {"n": 0, "k": 0, "tasks": {}})
    d["n"] += 1
    d["k"] += int(bool(m["success"]))
    d["tasks"][t.split("__", 1)[0]] = d["tasks"].get(t.split("__", 1)[0], 0) + int(bool(m["success"]))
for d in per.values():
    d["pass"] = d["n"] >= 3 and d["k"] >= 2
res = {"root": root, "objects": per, "n_objects": len(per), "n_pass": sum(d["pass"] for d in per.values()),
       "pass_ids": sorted(k for k, d in per.items() if d["pass"])}
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: res[k] for k in ("n_objects", "n_pass")}))
for k, d in sorted(per.items()):
    print(k, d["k"], "/", d["n"], "PASS" if d["pass"] else "")
