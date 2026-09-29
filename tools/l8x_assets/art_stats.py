"""Statistics of the articulated put-in episodes (xart; coordinator's list): per task and split -- generated
episodes, skipped layouts, success rate, overexposed (the first head frame > 10 % saturated after auto exposure),
name duplicates (the object's prompt name equal to another named thing in the scene), head at 0.785 rad.
usage: python tools/l8x_assets/art_stats.py OUT_DIR [JSON_OUT]"""
from __future__ import annotations

import glob
import json
import os
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    rows = {}
    for d in sorted(glob.glob(os.path.join(a[0], "*", "art_*", "*"))):
        split, fx = d.split(os.sep)[-3], d.split(os.sep)[-2]
        kind = fx.split("_")[1]
        r = rows.setdefault(f"{kind}|{split}", {"episodes": 0, "success": 0, "skipped": 0, "overexposed": 0,
                                                 "name_dup": 0, "head_0785": 0, "fixtures": set(), "reasons": {}})
        if os.path.exists(os.path.join(d, "skipped.json")):
            r["skipped"] += 1
            why = json.load(open(os.path.join(d, "skipped.json")))["reason"].split(":")[0][:40]
            r["reasons"][why] = r["reasons"].get(why, 0) + 1
            continue
        mp = os.path.join(d, "meta.json")
        if not os.path.exists(mp):
            continue
        m = json.load(open(mp))
        sc = json.load(open(os.path.join(d, "scene.json")))
        art = m.get("art") or {}
        r["episodes"] += 1
        r["success"] += bool(m["success"])
        iso = art.get("iso") or {}
        r["overexposed"] += bool(iso.get("overexposed") or (iso.get("sat") or 0) > 0.10)
        names = [sc["instruction"]]
        r["name_dup"] += int(len(set(n.lower() for n in names)) < len(names))
        r["head_0785"] += abs(float((art.get("head") or {}).get("tilt", 0)) - 0.785) < 1e-6
        r["fixtures"].add(fx[6:])
    for r in rows.values():
        r["fixtures"] = sorted(r["fixtures"])
        n = r["episodes"]
        r["success_rate"] = round(r["success"] / n, 3) if n else None
        r["head_ratio"] = round(r["head_0785"] / n, 3) if n else None
    out = json.dumps(rows, indent=1)
    print(out)
    if len(a) > 1:
        open(a[1], "w").write(out)


if __name__ == "__main__":
    main()
