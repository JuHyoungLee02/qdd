"""E-SR1c: privileged authority strata of the evaluation set (label-only, no model output) -- n_far / n_band / n_near
(docs/stage3/prereg_sr1c.md §0 'can this sample decide it').
  python tools/sr1c/strata.py --view /data/harvest/data/ma2/view --eval-set /data/harvest/data/ma2/eval_set.json \
      --out strata.json
Writes {id: {"a": a, "stratum": s, "phase": phase, "task": task, "dist": d}} + counts."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.train import sr1c_authority as A  # noqa: E402


def row_id(variant, task, row) -> str:
    return f"{variant}/{task}/{row['kind']}/ep{int(row['seed'])}/k{int(row['k'])}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", default="/data/harvest/data/ma2/view")
    ap.add_argument("--eval-set", default="/data/harvest/data/ma2/eval_set.json")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ids = json.load(open(a.eval_set))["ids"]
    want = set(ids)
    rec = {}
    for v in sorted(os.listdir(a.view)):
        for t in sorted(os.listdir(os.path.join(a.view, v))):
            for k in ("P0", "P1", "P2"):
                for suf in (".eval.stageb.jsonl", ".stageb.jsonl"):
                    p = os.path.join(a.view, v, t, k + suf)
                    if not os.path.exists(p):
                        continue
                    for x in open(p, encoding="utf-8"):
                        r = json.loads(x)
                        i = row_id(v, t, r)
                        if i in want and i not in rec:
                            d, c = A.stage_distance(r["aux"], r["phase_id"])
                            av = A.privileged(r["aux"], r["phase_id"])
                            rec[i] = {"a": av, "stratum": A.stratum(av), "phase": r["phase_id"], "task": t,
                                      "dist": d, "contact": c}
    miss = [i for i in ids if i not in rec]
    cnt = {}
    for i in ids:
        if i in rec:
            s = rec[i]["stratum"]
            cnt[s] = cnt.get(s, 0) + 1
            key = f"{rec[i]['task']}:{s}"
            cnt[key] = cnt.get(key, 0) + 1
    out = {"n": len(ids), "missing": len(miss), "counts": cnt, "ids": {i: rec[i] for i in ids if i in rec}}
    json.dump(out, open(a.out, "w"), indent=0)
    print(json.dumps({"n": len(ids), "missing": len(miss), "counts": cnt}), flush=True)


if __name__ == "__main__":
    main()
