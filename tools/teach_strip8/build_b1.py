"""E-STRIP8b data (prereg_strip8b.md §1): S-min and S-drop rows from the L8D b1 nd-xyz rows (G-id inside the builder),
then G-rows: the control ids with their repeat counts are the same in S-full (L8D train_v2), S-min and S-drop.
usage: python build_b1.py <b1 data dir> <out dir>"""
import json
import os
import sys
from collections import Counter

from harvest.teach_strip8 import dataset as D

src, out = sys.argv[1], sys.argv[2]
res = {arm: D.build(os.path.join(src, "train_nd-xyz.jsonl"), out, "train", arm, seed=0) for arm in ("s-min", "s-drop")}


def ctrl(p):
    c, n = Counter(), 0
    for x in open(p):
        r = json.loads(x)
        n += 1
        if r["kind"] == "control":
            c[r["id"]] += 1
    return c, n


full, n_full = ctrl(os.path.join(src, "train_v2.jsonl"))
g = {"s-full_rows": n_full, "s-full_control": sum(full.values())}
for arm in ("s-min", "s-drop"):
    c, n = ctrl(os.path.join(out, f"train_{arm}.jsonl"))
    g[arm] = {"rows": n, "control": sum(c.values()), "same_ids_and_repeats": c == full}
g["pass"] = all(g[a]["same_ids_and_repeats"] and g[a]["rows"] == n_full for a in ("s-min", "s-drop"))
print("BUILD " + json.dumps(res))
print("G_ROWS " + json.dumps(g))
