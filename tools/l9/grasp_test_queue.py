"""L9 v2 grasp test queue (pure): the next chunk of object ids for tools/l9/grasp_test.py, in priority order
(1) current L9 targets (assets9.objects() role9 target, v1 gate pass), (2) hollow / wide objects (bowls, mugs, cups:
catalog `inside` or gtest9.HOLLOW_WORDS), (3) the rest; only objects whose candidate npz exists and that are not
tested yet.
  python tools/l9/grasp_test_queue.py --grip ffw_sg2 --n 1024 --out ids.txt [--cats bottle,bowl,mug --per-cat 1]"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import assets9 as A9  # noqa: E402
from harvest.l9 import gtest9 as GT  # noqa: E402

ROOT = "/data/harvest/l9v2"


def priority(k: str, row: dict, targets: set) -> int:
    if k in targets:
        return 0
    cat = f"{row.get('category', '')} {row.get('name', '')} {row.get('l9cat', '')}".lower()
    if row.get("inside") or any(x in cat for x in GT.HOLLOW_WORDS):
        return 1
    return 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grip", required=True)
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rows", default=f"{ROOT}/rows_mesh.json")
    ap.add_argument("--cats", default="")
    ap.add_argument("--per-cat", type=int, default=1)
    a = ap.parse_args()
    rows = json.load(open(a.rows))
    targets = {k for k, r in A9.objects().items() if r.get("role9") == "target"}
    gdir, tdir = os.path.join(ROOT, "grasps", a.grip), os.path.join(ROOT, "tested", a.grip)
    have = {f[:-4] for f in os.listdir(gdir) if f.endswith(".npz")} if os.path.isdir(gdir) else set()
    done = {f[:-4] for f in os.listdir(tdir) if f.endswith(".npz")} if os.path.isdir(tdir) else set()
    todo = sorted((k for k in rows if k in have and k not in done and rows[k].get("body_rel")),
                  key=lambda k: (priority(k, rows[k], targets), k))
    if a.cats:
        pick = []
        for c in a.cats.split(","):
            pick += [k for k in todo if c in str(rows[k].get("l9cat", "")).lower() and k not in pick][:a.per_cat]
        todo = pick
    todo = todo[:a.n]
    with open(a.out, "w") as f:
        f.write("".join(k + "\n" for k in todo))
    n_pr = [sum(priority(k, rows[k], targets) == p for k in todo) for p in range(3)]
    print(json.dumps({"n": len(todo), "by_priority": n_pr, "have": len(have), "done": len(done),
                      "rows": len(rows), "targets_in_rows": len(targets & set(rows))}))


if __name__ == "__main__":
    main()
