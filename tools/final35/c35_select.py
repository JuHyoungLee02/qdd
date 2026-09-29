"""E-C35 checkpoint choice per seed (prereg_c35.md): the epoch with the lower L8S-validation >20 mm failure rate
(no goal = failure); tie -> higher open-pool validation hit rate; tie -> the later epoch. Prints the chosen merged dir.
usage: python c35_select.py <eval dir epoch1> <merged epoch1> <eval dir epoch2> <merged epoch2>"""
import json
import os
import sys


def score(d):
    e = []
    for x in open(os.path.join(d, "x_val_l8s_d-min_clean", "scores.jsonl")):
        r = json.loads(x)
        if r.get("approach_row"):
            v = r.get("approach_3d_mm")
            e.append(1e6 if v is None else float(v))
    g = [json.loads(x) for x in open(os.path.join(d, "g_val_open", "scores.jsonl"))]
    fail = sum(v > 20.0 for v in e) / max(1, len(e))
    hit = sum(bool(r.get("hit")) for r in g) / max(1, len(g))
    return fail, -hit


e1, m1, e2, m2 = sys.argv[1:5]
s1, s2 = score(e1), score(e2)
best = m1 if s1 < s2 else m2
json.dump({"epoch1": {"fail": s1[0], "hit": -s1[1]}, "epoch2": {"fail": s2[0], "hit": -s2[1]}, "chosen": best},
          open(os.path.join(os.path.dirname(e1), f"select_{os.path.basename(e1)}.json"), "w"), indent=1)
print(best)
