"""L9 v2 grasp test report (pure): pass rates of tools/l9/grasp_test.py results per family, width class,
(family, part) and per object (>= 8 valid candidates = the object stays a target of that robot, spec §12.4).
valid = shake_ok and, where the low-friction pass ran, lowfric_ok.
  python tools/l9/grasp_test_report.py --grip ffw_sg2 [--tested /data/harvest/l9v2/tested] [--json out.json]"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import gtest9 as GT  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grip", required=True)
    ap.add_argument("--tested", default="/data/harvest/l9v2/tested")
    ap.add_argument("--json", default="")
    ap.add_argument("--rows", default="/data/harvest/l9v2/rows_mesh.json")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.tested, a.grip, "*.npz")))
    agg = {k: defaultdict(lambda: [0, 0, 0, 0]) for k in ("family", "width", "family_part")}
    n_obj, n8, n0, per_obj = 0, 0, 0, {}
    rows = json.load(open(a.rows)) if os.path.exists(a.rows) else {}
    cat_of = lambda k: str(rows.get(k, {}).get("l9cat") or "?")
    cats = defaultdict(lambda: [0, 0, 0])  # objects with candidates, >= 8 valid, >= 8 shake ok
    tot = [0, 0, 0, 0]
    for f in files:
        r = np.load(f, allow_pickle=False)
        k = os.path.basename(f)[:-4]
        n_obj += 1
        if len(r["idx"]) == 0:
            n0 += 1
            per_obj[k] = 0
            continue
        lf = r["lowfric_ok"]
        valid = r["shake_ok"] & (lf != 0)  # lowfric -1 = not run
        per_obj[k] = int(valid.sum())
        n8 += per_obj[k] >= 8
        c = cats[cat_of(k)]
        c[0] += 1
        c[1] += per_obj[k] >= 8
        c[2] += int(r["shake_ok"].sum()) >= 8
        fam, part, w = r["family"], r["part"], r["w"]
        for j in range(len(valid)):
            row = (1, int(r["lift_ok"][j]), int(r["shake_ok"][j]), int(valid[j]))
            for key, val in (("family", fam[j]), ("width", GT.width_class(float(w[j]))),
                             ("family_part", f"{fam[j]}|{part[j]}")):
                e = agg[key][val]
                for i in range(4):
                    e[i] += row[i]
            for i in range(4):
                tot[i] += row[i]
    by_cat = {c: {"n": v[0], "ge8_valid": v[1], "ge8_shake": v[2]} for c, v in sorted(cats.items(), key=lambda x: -x[1][0])}
    out = {"grip": a.grip, "objects": n_obj, "objects_no_candidates": n0, "objects_ge8_valid": int(n8),
           "objects_ge8_shake": int(sum(v[2] for v in cats.values())), "by_l9cat": by_cat,
           "tests": tot[0], "lift": tot[1], "shake": tot[2], "valid": tot[3],
           **{k: {g: {"n": v[0], "lift": round(v[1] / max(v[0], 1), 3), "shake": round(v[2] / max(v[0], 1), 3),
                      "valid": round(v[3] / max(v[0], 1), 3)} for g, v in sorted(d.items())} for k, d in agg.items()}}
    print(json.dumps(out, indent=1))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(dict(out, per_object=per_obj), f)


if __name__ == "__main__":
    main()
