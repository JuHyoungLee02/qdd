"""E-H2H-T2 inputs: the 2,000-row C' and T1+T4 packs of the add run as standalone files (rows whose id is not a base id),
and the add_both arm (base 6,521 + C' 2,000 + the first 1,000 T1+T4 pack rows, seed-0 shuffle).
usage (pod): python -m xemb.h2h_packs H2H_DIR PACK_DIR"""
from __future__ import annotations

import json
import os
import sys

import numpy as np


def main(d, pk):
    rd = lambda n: [json.loads(x) for x in open(os.path.join(d, n), encoding="utf-8")]
    base = rd("h2h_base.jsonl")
    ids = {r["id"] for r in base}
    cp = [r for r in rd("add_cpx2.jsonl") if r["id"] not in ids]
    t4 = [r for r in rd("add_t1t4.jsonl") if r["id"] not in ids]
    assert len(cp) == 2000 and len(t4) == 2000, (len(cp), len(t4))
    os.makedirs(pk, exist_ok=True)
    for name, rows in (("cp_pack.jsonl", cp), ("t1t4_pack.jsonl", t4)):
        with open(os.path.join(pk, name), "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    both = base + cp + t4[:1000]
    rng = np.random.default_rng(0)
    with open(os.path.join(d, "add_both.jsonl"), "w", encoding="utf-8") as f:
        for i in rng.permutation(len(both)):
            f.write(json.dumps(both[i]) + "\n")
    print(json.dumps({"cp_pack": len(cp), "t1t4_pack": len(t4), "add_both": len(both)}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
