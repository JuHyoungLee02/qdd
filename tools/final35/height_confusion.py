"""Final 35B H 2-epoch drop on OOD-O: confusion of the answer's height intent (command.height) against the label, per
step (above_target / descend_close), with the approach 3D / xy error medians per cell — does a wrong height intent
explain the 3D error? usage: python height_confusion.py <data jsonl> <eval dir> [<eval dir> ...]"""
import collections
import json
import sys

import numpy as np


def height(text):
    try:
        d = json.loads(text[text.index("{"):text.rindex("}") + 1])
    except Exception:  # noqa: BLE001
        return "invalid"
    c = d.get("command") if isinstance(d.get("command"), dict) else {}
    return str(c.get("height", c.get("mode", "none")))


lab = {}
for x in open(sys.argv[1]):
    r = json.loads(x)
    if r.get("kind") == "control":
        lab[r["id"]] = height(r["answer"])
for e in sys.argv[2:]:
    rep = {json.loads(x)["id"]: json.loads(x)["text"] for x in open(f"{e}/replies.jsonl")}
    sc = [json.loads(x) for x in open(f"{e}/scores.jsonl")]
    a3 = [s["approach_3d_mm"] for s in sc if s.get("approach_row") and s.get("approach_3d_mm") is not None]
    print(f"== {e}  approach rows={sum(1 for s in sc if s.get('approach_row'))} with 3D={len(a3)} 3D_med={np.median(a3):.1f} "
          f"steps={dict(collections.Counter(s['step'] for s in sc if s.get('approach_row')))}")
    for step in ("above_target", "descend_close"):
        cells = collections.defaultdict(list)
        for s in sc:
            if s["step"] != step or s["id"] not in rep:
                continue
            cells[(lab.get(s["id"]), height(rep[s["id"]]))].append(s)
        print(f"  {step}")
        for (l, p), v in sorted(cells.items(), key=lambda kv: -len(kv[1])):
            d3 = [s["approach_3d_mm"] for s in v if s.get("approach_3d_mm") is not None]
            xy = [s["approach_xy_mm"] for s in v if s.get("approach_xy_mm") is not None]
            big3 = sum(1 for s in v if (s.get("approach_3d_mm") or 0) > 20); bigxy = sum(1 for s in v if (s.get("approach_xy_mm") or 0) > 20)
            print(f"    label={l:10s} pred={p:10s} n={len(v):4d} 3D>20mm={big3:3d} xy>20mm={bigxy:3d} 3D_med={np.median(d3) if d3 else None!s:>6} "
                  f"xy_med={np.median(xy) if xy else None!s:>6}")
