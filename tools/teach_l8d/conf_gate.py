"""Confuser gate (prereg_l8d change 10): clean truth per cf task in <gate root>/gate/*/*/meta.json, pass >= 8/10;
writes <out.json> and the train plan restricted to the passing tasks.
usage: python conf_gate.py <gate root> <out.json> <plan_conf.json> <plan_conf_pass.json>"""
import glob
import json
import os
import sys

from harvest.teach_l8d import spec as S

root, out, plan_in, plan_out = sys.argv[1:5]
per = {t: [0, 0] for t in S.CONF_TASKS}
for m in glob.glob(os.path.join(root, "gate", "*", "*", "meta.json")):
    m = json.load(open(m))
    if m.get("task") in per and m.get("style") == "clean":
        per[m["task"]][0] += 1
        per[m["task"]][1] += int(bool(m["success"]))
res = {t: {"n": n, "k": k, "pass": n >= 10 and k >= 8} for t, (n, k) in per.items()}
json.dump(res, open(out, "w"), indent=1)
ok = {t for t, r in res.items() if r["pass"]}
plan = [e for e in json.load(open(plan_in)) if e["task"] in ok]
json.dump(plan, open(plan_out, "w"), indent=0)
print(json.dumps({t: f"{r['k']}/{r['n']}" for t, r in res.items()}), "train", len(plan))
