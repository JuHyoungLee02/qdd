"""Split the unfinished episodes of each job line into chunk plans so one bucket can run in several Isaac processes.
usage: python split_left.py <jobs.txt> <collect root> <chunk size> <out dir>   -> <out dir>/chunk_<i>.json + chunks.txt"""
import glob
import json
import os
import sys


def arg(tok, name, default=None):
    return tok[tok.index(name) + 1] if name in tok else default


jobs, root, size, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
done = set()
for p in glob.glob(os.path.join(root, "*", "*", "*", "meta.json")) + \
        glob.glob(os.path.join(root, "*", "*", "*", "skipped.json")):
    ep = os.path.dirname(p)
    done.add((ep.split(os.sep)[-3], os.path.basename(ep)))
os.makedirs(out, exist_ok=True)
lines, k = [], 0
for line in open(jobs).read().splitlines():
    if not line.strip():
        continue
    t = line.split()
    plan = json.load(open(arg(t, "--plan")))
    sp, var, tz = arg(t, "--split"), arg(t, "--variant"), float(arg(t, "--table-z"))
    lift, fur, obj = arg(t, "--lift"), arg(t, "--furniture"), arg(t, "--objset")
    left = [e for e in plan
            if e["split"] == sp and e["variant"] == var and abs(float(e["table_z"]) - tz) < 1e-6
            and ((e.get("lift") is None) if lift is None else abs(float(e.get("lift") or 0) - float(lift)) < 1e-6)
            and e.get("furniture") == fur and e.get("objset") == obj
            and (e["split"], f"{e['task']}_s{e['seed']}") not in done]
    for i in range(0, len(left), size):
        f = os.path.join(out, f"chunk_{k}.json")
        json.dump(left[i:i + size], open(f, "w", newline="\n"), indent=0)
        t2 = list(t)
        t2[t2.index("--plan") + 1] = os.path.abspath(f)
        lines.append(" ".join(t2))
        k += 1
with open(os.path.join(out, "chunks.txt"), "w", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print("chunks", k, "episodes", sum(len(json.load(open(os.path.join(out, f"chunk_{i}.json")))) for i in range(k)))
