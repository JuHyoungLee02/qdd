"""E-H2H-T 'add' arms (prereg_h2h_add.md): base (h2h_base, 6,521 rows) + the SAME 2,000 pack rows the replacement arms
used (taken from h2h_t1t4 / h2h_cp: rows whose id is not a base id), shuffled with seed 0.
usage (pod): python -m xemb.h2h_add H2H_DIR"""
from __future__ import annotations

import json
import os
import sys

import numpy as np


def pack_rows(arm_rows, base_ids):
    return [r for r in arm_rows if r["id"] not in base_ids]


def main(d):
    rd = lambda n: [json.loads(x) for x in open(os.path.join(d, n), encoding="utf-8")]
    base = rd("h2h_base.jsonl")
    ids = {r["id"] for r in base}
    out = {}
    for src, name in (("h2h_t1t4.jsonl", "add_t1t4"), ("h2h_cp.jsonl.moved_to_cpg1", "add_cp")):
        pk = pack_rows(rd(src), ids)
        assert len(pk) == 2000, (src, len(pk))
        rows = base + pk
        rng = np.random.default_rng(0)
        with open(os.path.join(d, name + ".jsonl"), "w", encoding="utf-8") as f:
            for i in rng.permutation(len(rows)):
                f.write(json.dumps(rows[i]) + "\n")
        out[name] = {"rows": len(rows), "base": len(base), "pack": len(pk)}
    json.dump(out, open(os.path.join(d, "add_counts.json"), "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main(sys.argv[1])
