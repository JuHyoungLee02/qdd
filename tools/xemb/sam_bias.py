"""SAM filter bias check (user-log 171 (2)): per source, obj / place point rows before (records + records_G) and after
(records_verified + records_verified_G) the SAM filter, grouped by category = head noun of the name; pass rate per
category, and the rejected pool written for the second-detector test.
usage (pod): python -m xemb.sam_bias POINTS_ROOT OUT_JSON REJECTED_JSONL SOURCE [...]"""
from __future__ import annotations

import json
import os
import sys


def rows(p):
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


def main(root, outp, rej_p, srcs):
    res, rej = {}, []
    for s in srcs:
        d = os.path.join(root, s)
        allr = [r for r in rows(f"{d}/records.jsonl") + rows(f"{d}/records_G.jsonl") if r["qa_kind"] != "ee_point"]
        kept = {r["id"] for r in rows(f"{d}/records_verified.jsonl") + rows(f"{d}/records_verified_G.jsonl")}
        cat = {}
        for r in allr:
            c = (r.get("name") or "?").split()[-1]
            e = cat.setdefault(c, [0, 0])
            e[0] += 1
            if r["id"] in kept:
                e[1] += 1
            elif not r.get("exclude"):
                rej.append(dict(r, src=s))
        top = sorted(cat.items(), key=lambda kv: -kv[1][0])[:15]
        tot = sum(v[0] for v in cat.values())
        res[s] = {"rows": tot, "pass": sum(v[1] for v in cat.values()),
                  "by_category": {k: {"n": v[0], "pass_rate": round(v[1] / v[0], 3)} for k, v in top}}
    json.dump(res, open(outp, "w"), indent=1)
    with open(rej_p, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rej)
    print(json.dumps(res, indent=1)[:4000])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
