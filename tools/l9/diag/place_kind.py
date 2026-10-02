"""L9 v2 diagnosis: place-stage failures by place kind (pure): the place key of the failed placement is a catalog object
(l9o_* / l9c_*: stacking onto / into an object), a spot / surface (s9_*), or other.
usage: python tools/l9/diag/place_kind.py <collect root> [--since EPOCH]"""
import glob
import json
import os
import sys
from collections import Counter


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    c, defs = Counter(), Counter()
    for m in glob.glob(os.path.join(a[0], "**", "meta.json"), recursive=True):
        if os.path.getmtime(m) < since:
            continue
        meta = json.load(open(m))
        if meta.get("grasp_v2") is None:
            continue
        ep = os.path.dirname(m)
        labs = [json.loads(l) for l in open(os.path.join(ep, "labels.jsonl"))]
        if not any(l.get("step") == "lower_open" for l in labs):
            continue
        rp = os.path.join(ep, "result.json")
        res = json.load(open(rp)) if os.path.exists(rp) else {}
        last_place = [l.get("place") for l in labs if l.get("step") == "lower_open"][-1]
        kind = "object" if str(last_place).startswith(("l9o_", "l9c_")) else ("spot" if str(last_place).startswith("s9_") else "other")
        ok = bool(meta.get("success"))
        c[(kind, "ok" if ok else ("tipped" if res.get("tipped") else "fail"))] += 1
        if not ok:
            defs[(kind, meta.get("task_id"))] += 1
    print(sorted(c.items()))
    print(defs.most_common(25))


if __name__ == "__main__":
    main()
