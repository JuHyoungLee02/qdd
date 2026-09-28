"""E-STAGE8 builds (prereg_stage8.md): the head-view open point cell of E-VIEW8 (view8_build.classify: training copies,
no wide-angle, no third-person, G rows split off and guarded) added to the L8-X b2 base.
  train_mix.jsonl    : base + 75 % open (= M, and stage 1 of S)
  train_post.jsonl   : base + 15 % open replay (stage 2 of S)
Open rows are drawn without replacement inside each pass over the cell (seed 8), as in E-OPRATIO8.
usage: python stage8_build.py <out dir> <base d-min jsonl>"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import view8_build as VB  # noqa: E402


def draw(rows, need, seed):
    rng = np.random.default_rng(seed)
    idx = np.concatenate([rng.permutation(len(rows)) for _ in range(need // len(rows) + 1)])[:need]
    return [rows[int(i)] for i in idx]


def write(out, name, base, rows):
    lines = base + [json.dumps(r) for r in rows]
    order = np.random.default_rng([8, len(lines)]).permutation(len(lines))
    with open(os.path.join(out, f"train_{name}.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for i in order:
            f.write(lines[int(i)] + "\n")
    return {"base": len(base), "open": len(rows), "total": len(lines)}


def main(out, base_p):
    os.makedirs(out, exist_ok=True)
    base = open(base_p, encoding="utf-8").read().splitlines()
    cells, counts = VB.classify(VB.HEAD_FILES + VB.MIXED_FILES)
    head = cells["head"]
    res = {"head_cell": len(head), "files": counts}
    res["mix"] = write(out, "mix", base, draw(head, int(round(len(base) * 0.75)), 8))
    res["post"] = write(out, "post", base, draw(head, int(round(len(base) * 0.15)), 9))
    res["mix"]["cell_repeat"] = round(res["mix"]["open"] / len(head), 3)
    json.dump(res, open(os.path.join(out, "build.counts.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "files"}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
