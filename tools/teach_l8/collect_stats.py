"""Collection summary for E-TEACH-L8 (results doc): episodes, success by style x task x variant, perturbations,
labelled / dropped rows by reason, wall time. usage: python collect_stats.py <collect root>/<split>"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

root = sys.argv[1]
metas = [json.load(open(p)) for p in glob.glob(os.path.join(root, "*", "*", "meta.json"))]
by = defaultdict(lambda: [0, 0])
for m in metas:
    k = f"{m['style']}|{m['task']}|{m['variant']}"
    by[k][0] += 1
    by[k][1] += int(m["success"])
drops, rows, kinds = Counter(), 0, Counter()
for p in glob.glob(os.path.join(root, "*", "*", "labels.jsonl")):
    for line in open(p):
        r = json.loads(line)
        rows += 1
        drops[r["drop"] or "kept"] += 1
        if r["drop"]:
            drops[f"{r['drop']}|{r['step']}|{r['task']}"] += 1
        kinds[r["exec_kind"]] += 1
walls = sorted(m["wall_s"] for m in metas if m.get("wall_s") is not None)
out = {"episodes": len(metas), "success": sum(m["success"] for m in metas),
       "by_style_task_variant": {k: {"n": v[0], "success": v[1]} for k, v in sorted(by.items())},
       "end_reason": dict(Counter(m["end_reason"] for m in metas)), "rows": rows, "rows_by_drop": dict(drops),
       "exec_kind": dict(kinds), "n_perturb_total": sum(m["n_perturb"] for m in metas),
       "wall_s_median": walls[len(walls) // 2] if walls else None, "wall_s_sum": round(sum(walls), 1)}
print(json.dumps(out, indent=1))
