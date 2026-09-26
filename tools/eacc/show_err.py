"""Print the invalid rows of a run (arm, snap, errors, the raw answer's segment / command part) -- format debugging.
usage: python tools/eacc/show_err.py rows.jsonl [--chars 400]"""
from __future__ import annotations

import argparse
import json


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("--chars", type=int, default=400)
    a = ap.parse_args(argv)
    for line in open(a.rows):
        r = json.loads(line)
        if r["valid"]:
            continue
        raw = r.get("raw") or ""
        i = raw.find('"segment"')
        print(r["arm"], r["snap"], r["errors"])
        print("   ", (raw[i:i + a.chars] if i >= 0 else raw[-a.chars:]).replace("\n", " "))


if __name__ == "__main__":
    main()
