"""objects_real rows of the L8S target list (L8-D plan5/l8s_targets.json "targets") for run_art.
usage: python tools/l8x_assets/art_targets.py TARGETS.json OBJECTS_REAL.json OUT.json"""
from __future__ import annotations

import json
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    ids = json.load(open(a[0]))["targets"]
    rows = json.load(open(a[1]))["objects"]
    out = {k: rows[k] for k in ids if k in rows}
    json.dump(out, open(a[2], "w"))
    print(len(ids), "targets,", len(out), "rows")


if __name__ == "__main__":
    main()
