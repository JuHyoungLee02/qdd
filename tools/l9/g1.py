"""L9 G1 per-definition pilot verdict over one or more collect roots (pure).
A pilot episode counts as a success only with success and no arm jump (max_dq_rad <= 0.04). pass = n >= --min-n and
yield >= 0.5. Skipped rows (the definition did not fit the drawn scenes) are reported, not counted.
usage: python tools/l9/g1.py <out.json> <collect root>... [--min-n 10]"""
import glob
import json
import os
import sys
from collections import defaultdict

args = [a for a in sys.argv[1:] if not a.startswith("--")]
min_n = int(sys.argv[sys.argv.index("--min-n") + 1]) if "--min-n" in sys.argv else 10
args = [a for a in args if a != str(min_n)]
out_path, roots = args[0], args[1:]
res = defaultdict(lambda: [0, 0, 0])
arm = defaultdict(lambda: [0, 0])
fam = {}
for root in roots:
    for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
        meta = json.load(open(m))
        if meta.get("gen") != "l9" or meta.get("task_id") == "gate_move":
            continue
        k = meta["task_id"]
        fam[k] = meta.get("task_family")
        ok = bool(meta["success"]) and (meta.get("max_dq_rad") or 0) <= 0.04
        res[k][0] += 1
        res[k][1] += ok
        arm[meta["arm"]][0] += 1
        arm[meta["arm"]][1] += ok
    for s in glob.glob(os.path.join(root, "**", "skipped.json"), recursive=True):
        r = json.load(open(s)).get("row") or {}
        if r.get("def") and r["def"] != "gate_move":
            res[r["def"]][2] += 1
defs = {k: {"family": fam.get(k), "n": v[0], "ok": v[1], "skipped": v[2],
            "yield": round(v[1] / v[0], 3) if v[0] else None} for k, v in sorted(res.items())}
ok = sorted(k for k, v in defs.items() if v["n"] >= min_n and v["yield"] >= 0.5)
fail = sorted(k for k, v in defs.items() if v["n"] >= min_n and v["yield"] < 0.5)
short = sorted(k for k, v in defs.items() if v["n"] < min_n)
by_fam = defaultdict(int)
for k in ok:
    by_fam[defs[k]["family"]] += 1
rep = {"min_n": min_n, "pass": ok, "fail": fail, "short": short, "n_pass": len(ok), "pass_by_family": dict(by_fam),
       "arm": {a: {"n": v[0], "ok": v[1]} for a, v in arm.items()}, "definitions": defs}
json.dump(rep, open(out_path, "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("n_pass", "pass_by_family", "arm")}))
print("fail", [(k, defs[k]["yield"]) for k in fail])
print("short", [(k, defs[k]["n"], defs[k]["skipped"]) for k in short])
