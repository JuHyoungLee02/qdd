"""Print the top-level type / size and the first record of a (gzipped) JSON file, truncated.
usage: python tools/l8x_assets/peek_json.py FILE.json[.gz] [n_chars]"""
from __future__ import annotations

import gzip
import json
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    op = gzip.open if a[0].endswith(".gz") else open
    with op(a[0], "rt") as f:
        d = json.load(f)
    n = int(a[1]) if len(a) > 1 else 3000
    if isinstance(d, dict):
        k = next(iter(d))
        print("dict", len(d), "first key", k)
        print(json.dumps(d[k])[:n])
    else:
        print("list", len(d))
        print(json.dumps(d[0])[:n])


if __name__ == "__main__":
    main()
