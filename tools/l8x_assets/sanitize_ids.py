"""Rename the object ids of a table to prim-path safe ids (import_products.safe_id); uid follows the key.
usage: python tools/l8x_assets/sanitize_ids.py TABLE.json"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from tools.l8x_assets.import_products import safe_id  # noqa: E402


def main(argv=None):
    p = (argv or sys.argv[1:])[0]
    t = json.load(open(p))
    out, n = {}, 0
    for k, o in t["objects"].items():
        k2 = safe_id(k)
        n += k2 != k
        if k2 in out:
            raise ValueError(f"id clash {k2}")
        out[k2] = dict(o, uid=k2) if "uid" in o else o
    t["objects"] = out
    json.dump(t, open(p, "w"), indent=1)
    print("renamed", n, "of", len(out))


if __name__ == "__main__":
    main()
