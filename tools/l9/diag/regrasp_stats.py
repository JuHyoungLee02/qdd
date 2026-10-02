"""L9 v2 diagnosis: what happens after a P2 re-grasp (EMPTY / WIDE close) (pure).
usage: python tools/l9/diag/regrasp_stats.py <collect root> [...] [--since EPOCH] [--robot NAME]
For every pick record with a regrasp_trace: the next pick record of the same object (the re-grasp) -> its close
outcome / choice failure / fallback, the target's displacement between the close call and the next call (labels gt),
and episode success."""
import glob
import json
import os
import sys
from collections import Counter

import numpy as np


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    robot = a[a.index("--robot") + 1] if "--robot" in a else None
    c = Counter()
    for root in [x for x in a if os.path.isdir(x)]:
        for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            g = meta.get("grasp_v2")
            if g is None or (robot and g.get("robot_profile") != robot):
                continue
            picks = g.get("picks", [])
            labs = [json.loads(l) for l in open(os.path.join(os.path.dirname(m), "labels.jsonl"))]
            # target displacement right after each close call (descend_close -> next call)
            moves = []
            for x, y in zip(labs, labs[1:]):
                if x.get("step") == "descend_close" and x.get("tgt") == y.get("tgt"):
                    moves.append(float(np.linalg.norm(np.subtract(y["gt"]["tgt"][:2], x["gt"]["tgt"][:2]))) * 1e3)
            for i, p in enumerate(picks):
                tr = (p.get("timeline") or {}).get("regrasp_trace")
                if not tr:
                    continue
                nxt = picks[i + 1] if i + 1 < len(picks) else {}
                tl = nxt.get("timeline") or {}
                res = nxt.get("choice_fail") or tl.get("outcome_close") or (
                    "fallback:" + tl["fallback_trace"][-1]["status"] if tl.get("fallback_trace") else "none")
                c[(g.get("robot_profile"), tr[-1]["outcome"], res, bool(meta.get("success")))] += 1
            if moves:
                c[("close_push_mm>15", g.get("robot_profile"), sum(v > 15 for v in moves), len(moves))] += 0
                c[("closes", g.get("robot_profile"))] += len(moves)
                c[("closes_push>15mm", g.get("robot_profile"))] += sum(v > 15 for v in moves)
    for k, v in sorted(c.items(), key=lambda x: str(x[0])):
        if v:
            print(k, v)


if __name__ == "__main__":
    main()
