"""Freeze the G split (user-log 166) before training: write the RB2 T4 held-out episode list, then list every G group
of the converted point sources with counts and a digest -> MANIFEST json (committed as docs/stage3/gsplit_g166.json).
usage (pod): python -m xemb.gsplit_freeze MARR_REAL_ROOT POINTS_ROOT MANIFEST_OUT"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

from . import gsplit as GS


def rb2_test(root):
    from .src_rb2 import load
    eps = load(root)
    order = np.random.default_rng(0).permutation(len(eps))
    return sorted(int(eps[i]["ep"]) for i in order[: len(eps) // 5])


def main(marr, pts, outp):
    test = rb2_test(marr)
    os.makedirs(os.path.dirname(GS.RB2_TEST_FILE), exist_ok=True)
    json.dump(test, open(GS.RB2_TEST_FILE, "w"))
    GS._rb2_test = set(test)
    man = {"rule": f"sha256('g166|<family>|<group>') % 100 < {GS.PCT}; RB2 also its T4 held-out episodes",
           "rb2_t4_test_episodes": test, "benchmarks": GS.BENCHMARKS, "sources": {}}
    for s in sorted(os.listdir(pts)):
        p = os.path.join(pts, s, "records.jsonl")
        if not os.path.exists(p):
            continue
        rows = [json.loads(x) for x in open(p)]
        gp = os.path.join(pts, s, "records_G.jsonl")
        rows += [json.loads(x) for x in open(gp)] if os.path.exists(gp) else []
        tr, g = GS.split(rows)
        groups = sorted({GS.group_of(r)[1] for r in g if GS.group_of(r)})
        man["sources"][s] = {"rows": len(rows), "g_rows": len(g), "train_rows": len(tr), "g_groups": groups}
        with open(os.path.join(pts, s, "records.jsonl"), "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in tr)
        with open(gp, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in g)
    man["digest"] = hashlib.sha256(json.dumps(man["sources"], sort_keys=True).encode()).hexdigest()[:16]
    json.dump(man, open(outp, "w"), indent=1)
    print(json.dumps({k: {kk: v[kk] for kk in ("rows", "g_rows")} for k, v in man["sources"].items()}), man["digest"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
