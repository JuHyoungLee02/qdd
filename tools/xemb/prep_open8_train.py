"""E-OPEN8 (prereg docs/stage3/prereg_open8.md §1, §4.1): training files for harvest.teach_l8.train and the held-out set.
  train_oa.jsonl   the 6,500 E-OPEN8 rows as L8-loader rows (kind 'aux' = prompt text inline; xkind keeps ours)
  train_ob.jsonl   3,261 random L8 train rows (seed 0) + 3,250 random E-OPEN8 rows (seed 0), shuffled
  heldout.jsonl    50 rows per stream from converted rows NOT in train.jsonl (seed 1)
usage (pod): python -m xemb.prep_open8_train OPEN8_DIR L8_TRAIN_JSONL
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from .build_open8 import load_rows, row_ok


def as_l8(r: dict) -> dict:
    return {"id": r["id"], "kind": "aux", "xkind": r.get("qa_kind") or r["kind"], "stream": r.get("stream", ""),
            "source": r.get("source", ""), "frame": r.get("frame", ""), "prompt": r["prompt"], "images": r["images"],
            "answer": r["answer"]}


def main(d, l8_train):
    open_rows = [json.loads(x) for x in open(os.path.join(d, "train.jsonl"), encoding="utf-8")]
    oa = [as_l8(r) for r in open_rows]
    with open(os.path.join(d, "train_oa.jsonl"), "w", encoding="utf-8") as f:
        for r in oa:
            f.write(json.dumps(r) + "\n")
    l8 = [json.loads(x) for x in open(l8_train, encoding="utf-8")]
    rng = np.random.default_rng(0)
    ob = [l8[i] for i in rng.permutation(len(l8))[:3261]] + [oa[i] for i in rng.permutation(len(oa))[:3250]]
    ob = [ob[i] for i in rng.permutation(len(ob))]
    with open(os.path.join(d, "train_ob.jsonl"), "w", encoding="utf-8") as f:
        for r in ob:
            f.write(json.dumps(r) + "\n")
    plan = json.load(open(os.path.join(d, "plan.json")))
    used = {r["id"] for r in open_rows}
    rng1 = np.random.default_rng(1)
    held = []
    for s in plan["streams"]:
        cand = [r for r in load_rows(s["path"], s.get("filter")) if r["id"] not in used]
        base = os.path.dirname(os.path.dirname(os.path.abspath(s["path"])))
        for r in cand:
            r["images"] = [p if os.path.isabs(p) else os.path.join(base, p) for p in r["images"]]
        take = 0
        for i in rng1.permutation(len(cand)):
            if take >= 50:
                break
            if row_ok(cand[i])[0]:
                held.append(as_l8(dict(cand[i], stream=s["name"])))
                take += 1
    with open(os.path.join(d, "heldout.jsonl"), "w", encoding="utf-8") as f:
        for r in held:
            f.write(json.dumps(r) + "\n")
    out = {"train_oa": len(oa), "train_ob": len(ob), "ob_from_l8": 3261, "ob_from_open": 3250, "heldout": len(held),
           "heldout_by_stream": {s["name"]: sum(r["stream"] == s["name"] for r in held) for s in plan["streams"]}}
    json.dump(out, open(os.path.join(d, "train_files.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
