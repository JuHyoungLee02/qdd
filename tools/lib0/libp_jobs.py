"""E-LIBP job list (prereg_libp.md): per suite x category, the 5 tasks with the smallest sha256("libp|<suite>|<name>"),
1 episode (init state 0) -> lines "<suite>\t<task index>\t0" and a meta json (task index -> category, name, language).
Run with the LIBERO-plus package (LIB0_BENCH=plus env). usage: libp_jobs.py <out dir>"""
import hashlib
import json
import os
import sys

from libero.libero import benchmark

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
here = os.path.dirname(benchmark.__file__)
cls = json.load(open(os.path.join(here, "task_classification.json")))
bd = benchmark.get_benchmark_dict()
lines, meta = [], {}
for suite, items in cls.items():
    if suite not in bd:
        print("skip suite", suite)
        continue
    ts = bd[suite]()
    names = ts.get_task_names()
    idx = {n: i for i, n in enumerate(names)}
    cats = sorted({it["category"] for it in items})
    for c in cats:
        cand = [it["name"] for it in items if it["category"] == c and it["name"] in idx]
        pick = sorted(cand, key=lambda n: hashlib.sha256(f"libp|{suite}|{n}".encode()).hexdigest())[:5]
        for n in pick:
            i = idx[n]
            lines.append(f"{suite}\t{i}\t0")
            meta[f"{suite}|{i}"] = {"category": c, "name": n, "language": ts.get_task(i).language}
    print(suite, len(names), {c: sum(1 for it in items if it["category"] == c) for c in cats})
open(os.path.join(out, "jobs.txt"), "w").write("\n".join(lines) + "\n")
json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
print("jobs", len(lines))
