"""Print the assessment evidence and command of chosen rows (arm, snap) -- reading answers for the results doc.
usage: python tools/eacc/show_ans.py rows.jsonl --arm v2_ax --snaps off_a_00,off_c_00 [--chars 500]"""
from __future__ import annotations

import argparse
import json


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--snaps", required=True)
    ap.add_argument("--chars", type=int, default=500)
    a = ap.parse_args(argv)
    want = set(a.snaps.split(","))
    for line in open(a.rows):
        r = json.loads(line)
        if r["arm"] != a.arm or r["snap"] not in want:
            continue
        try:
            d = json.loads(r["raw"])
            s = d.get("assessment", {})
            print(r["snap"], r.get("command"), s.get("execution"), s.get("intent"), s.get("confidence"),
                  json.dumps(d.get("segment")), "|", (s.get("evidence") or "")[:a.chars])
        except (ValueError, TypeError):
            print(r["snap"], "RAW", (r.get("raw") or "")[:a.chars])


if __name__ == "__main__":
    main()
