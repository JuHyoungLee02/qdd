"""E-VIEW8 census: open point rows by file x view x qa_kind x camera (from the image file name), before and after
the G split. usage: python view_census.py <out json> [extra jsonl ...]"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from xemb import gsplit as GS  # noqa: E402
import opratio_build as OB  # noqa: E402

CAMS = ("gopro", "zed2", "droid_shoulder", "wrist", "head", "front", "rgb", "exo", "third")


def camera(r):
    b = os.path.basename((r.get("images") or [""])[0]).lower()
    for c in CAMS:
        if c in b:
            return c
    return re.sub(r"[\d_]+", "_", b)[:30]


def main(outp, extra):
    files = [os.path.join(OB.X, s, "records_verified.jsonl") for s in OB.SOURCES] + list(OB.PACKS) + extra
    res = {}
    for f in files:
        rows = OB._rows(f)
        keep, g = GS.split(rows) if rows else ([], [])
        c = collections.Counter((r.get("view"), r.get("qa_kind"), camera(r)) for r in keep)
        res[f] = {"n": len(rows), "g_rows": len(g), "cells": {" | ".join(map(str, k)): v for k, v in sorted(c.items())}}
    json.dump(res, open(outp, "w"), indent=1)
    for f, v in res.items():
        print(f, v["n"], "g", v["g_rows"])
        for k, n in v["cells"].items():
            print("   ", k, n)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
