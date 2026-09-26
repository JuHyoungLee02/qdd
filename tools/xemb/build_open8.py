"""E-OPEN8 (user-log 123 series: "일단 오픈소스를 가지고 학습을 할건데 ... 소규모로"): a small OPEN-SOURCE-ONLY training
set about the size of one L8 epoch (6,521 rows), mixed from the converted open streams that passed their gates.
Every row keeps its source / frame header and camera line; control rows use our runtime answer schema; the builder
refuses rows whose answer leaks a foreign key (fmt.leak_flags) and rows whose image file is missing.

usage (pod): python -m xemb.build_open8 OUT PLAN_JSON
  PLAN_JSON = {"streams": [{"name", "path" (records jsonl), "n", "filter" (optional qa_kind / kind list)}], "seed": 0}
Writes OUT/train.jsonl (shuffled), OUT/counts.json.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from . import fmt as F


def load_rows(path, kinds=None):
    rows = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        k = r.get("qa_kind") or r.get("kind")
        if kinds and k not in kinds:
            continue
        rows.append(r)
    return rows


def row_ok(r) -> tuple:
    if any(not os.path.exists(p) for p in r.get("images", [])):
        return False, "missing_image"
    if r.get("kind") == "control_xemb":
        if F.leak_flags(r["answer"], {"x": [-9, 9], "y": [-9, 9], "z": [-9, 9]}):
            return False, "foreign_key_in_answer"
    lines = r["prompt"].splitlines()
    if len(lines) < 2 or not lines[0].startswith("source: ") or not lines[1].startswith("frame: "):
        return False, "no_source_frame_header"
    return True, ""


def build(out, plan):
    rng = np.random.default_rng(plan.get("seed", 0))
    os.makedirs(out, exist_ok=True)
    rows, counts = [], {}
    for s in plan["streams"]:
        cand = load_rows(s["path"], s.get("filter"))
        base = os.path.dirname(os.path.dirname(os.path.abspath(s["path"])))  # converters write paths relative to it
        for r in cand:
            r["images"] = [p if os.path.isabs(p) else os.path.join(base, p) for p in r.get("images", [])]
        idx = rng.permutation(len(cand))
        took, rej = 0, {}
        for i in idx:
            if took >= s["n"]:
                break
            ok, why = row_ok(cand[i])
            if not ok:
                rej[why] = rej.get(why, 0) + 1
                continue
            r = dict(cand[i], stream=s["name"])
            rows.append(r)
            took += 1
        counts[s["name"]] = {"available": len(cand), "taken": took, "target": s["n"], "rejected": rej}
    order = rng.permutation(len(rows))
    with open(os.path.join(out, "train.jsonl"), "w", encoding="utf-8") as f:
        for i in order:
            f.write(json.dumps(rows[i]) + "\n")
    summ = {"total": len(rows), "streams": counts,
            "by_frame": {k: sum(r["frame"] == k for r in rows) for k in sorted({r["frame"] for r in rows})},
            "by_kind": {k: sum((r.get("qa_kind") or r["kind"]) == k for r in rows)
                        for k in sorted({r.get("qa_kind") or r["kind"] for r in rows})}}
    json.dump(summ, open(os.path.join(out, "counts.json"), "w"), indent=1)
    return summ


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1], json.load(open(sys.argv[2]))), indent=1))
