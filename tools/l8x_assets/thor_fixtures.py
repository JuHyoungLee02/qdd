"""THOR display fixtures for the b4 display gate: the per-piece gate passes (docs/stage3/l8x_b4_pieces.json) of the
shelf / counter kinds (dressers, TV stands, cabinets, counters), as a mesh table (assets_table rows) for
gate_display.py.
usage: python tools/l8x_assets/thor_fixtures.py PIECES.json ASSETS_TABLE.json OUT.json"""
from __future__ import annotations

import json
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    passed = json.load(open(a[0]))["pass"]
    table = json.load(open(a[1]))["assets"]
    out = {n: table[n] for n in passed if table[n]["category"] in ("shelf", "counter")}
    json.dump({"source": "assets_table.json (THOR, CC BY 4.0) / b4 piece gate", "assets": out}, open(a[2], "w"),
              indent=1)
    print(len(out), sorted(out))


if __name__ == "__main__":
    main()
