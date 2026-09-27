"""Keep only the job lines whose bucket (split, variant, table height, lift, furniture, objset) still has planned
episodes without meta.json / skipped.json (saves ~2.7 min Isaac boot per finished bucket).
usage: python jobs_left.py <jobs.txt> <collect root> <out jobs.txt>"""
import glob
import json
import os
import sys


def arg(tok, name, default=None):
    return tok[tok.index(name) + 1] if name in tok else default


jobs, root, out = sys.argv[1:4]
done = set()
for p in glob.glob(os.path.join(root, "*", "*", "*", "meta.json")) + \
        glob.glob(os.path.join(root, "*", "*", "*", "skipped.json")):
    ep = os.path.dirname(p)
    done.add((ep.split(os.sep)[-3], os.path.basename(ep)))
plans, keep = {}, []
for line in open(jobs).read().splitlines():
    if not line.strip():
        continue
    t = line.split()
    pf = arg(t, "--plan")
    plan = plans.setdefault(pf, json.load(open(pf)))
    sp, var, tz = arg(t, "--split"), arg(t, "--variant"), float(arg(t, "--table-z"))
    lift, fur, obj = arg(t, "--lift"), arg(t, "--furniture"), arg(t, "--objset")
    n = sum(1 for e in plan
            if e["split"] == sp and e["variant"] == var and abs(float(e["table_z"]) - tz) < 1e-6
            and (lift is None or abs(float(e.get("lift") or 0) - float(lift)) < 1e-6) and (lift is not None or e.get("lift") is None or fur)
            and e.get("furniture") == fur and e.get("objset") == obj
            and (e["split"], f"{e['task']}_s{e['seed']}") not in done)
    if n:
        keep.append(line)
with open(out, "w", newline="\n") as f:
    f.write("\n".join(keep) + ("\n" if keep else ""))
print("kept", len(keep), "of", len(open(jobs).read().splitlines()))
