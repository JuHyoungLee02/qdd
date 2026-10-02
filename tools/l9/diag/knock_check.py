"""L9 v2 diagnosis: in failed multi-step episodes, was an already placed target knocked / moved later (pure)?
usage: python tools/l9/diag/knock_check.py <collect root> [...] [--since EPOCH]
For each failed episode with >= 2 targets in its labels: the targets in order, result.json knocked / moved_mm, and
for every earlier target its position at the call after it was released vs at the last call (mm moved), plus the
truth step that was running when it first moved by > 1 cm."""
import glob
import json
import os
import sys

import numpy as np


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    n = moved_n = 0
    for root in [x for x in a if os.path.isdir(x)]:
        for m in sorted(glob.glob(os.path.join(root, "**", "meta.json"), recursive=True)):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            if meta.get("grasp_v2") is None or meta.get("success"):
                continue
            ep = os.path.dirname(m)
            labs = [json.loads(l) for l in open(os.path.join(ep, "labels.jsonl"))]
            order = []
            for l in labs:
                if l.get("tgt") and (not order or order[-1] != l["tgt"]):
                    order.append(l["tgt"])
            if len(order) < 2:
                continue
            n += 1
            res = json.load(open(os.path.join(ep, "result.json"))) if os.path.exists(os.path.join(ep, "result.json")) else {}
            out = []
            for k in order[:-1]:
                idx = [i for i, l in enumerate(labs) if l.get("tgt") != k and i > max(j for j, x in enumerate(labs) if x.get("tgt") == k)]
                if not idx:
                    continue
                def pos(l):
                    g = l.get("gt") or {}
                    if g.get("tgt") is not None and l.get("tgt") == k:
                        return g["tgt"]
                    return (g.get("others") or {}).get(k)
                p0 = pos(labs[idx[0]])
                if p0 is None:
                    continue
                first = None
                for i in idx:
                    p = pos(labs[i])
                    if p is not None and np.linalg.norm(np.subtract(p, p0)) > 0.01:
                        first = (labs[i].get("call"), labs[i - 1].get("step"))
                        break
                pl = pos(labs[idx[-1]])
                d = None if pl is None else round(float(np.linalg.norm(np.subtract(pl, p0))) * 1e3, 1)
                out.append((k[:12], d, first))
                moved_n += bool(d and d > 10)
            print(f"{os.path.relpath(ep, root)[:60]:60s} end={meta.get('end_reason')} knocked={[x[:12] for x in res.get('knocked', [])]} earlier={out}")
    print(f"\nmulti-target failed episodes {n}, earlier target moved > 1 cm afterwards: {moved_n}")


if __name__ == "__main__":
    main()
