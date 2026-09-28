"""Chain of gate_articulated.py processes over the scan (scan_articulated.py) of THOR articulated assets: the
fixture kinds of user-log 176 (fridges, microwaves, dressers / desks / side tables, doorways, faucets, stove knobs,
toasters, laptops, safes, toilets; boxes skipped), BATCH assets per Isaac process.
usage: python tools/l8x_assets/articulated_chain.py SCAN.json CODE_DIR GPU OUT_DIR CHAIN.sh [--only a,b]"""
from __future__ import annotations

import json
import sys

KEEP = ("Fridge", "Microwave", "Dresser", "Desk", "Side_Table", "Doorway", "Bathroom_Faucet", "Bathtub_Faucet",
        "Kitchen_Faucet", "StoveKnob", "Toaster", "Laptop", "Safe", "Toilet", "IKEACabinet", "Shelving_Unit",
        "Clothes_Dryer", "Washing_Machine", "coffee_machine", "TV_Stand")
BATCH = 6


def main(argv=None):
    a = argv or sys.argv[1:]
    scan = json.load(open(a[0]))
    code, gpu, out, chain = a[1], a[2], a[3], a[4]
    only = set(a[6].split(",")) if len(a) > 6 and a[5] == "--only" else None
    names = sorted(n for n, r in scan.items() if r["package"].startswith(KEEP) and (only is None or n in only))
    usds = [scan[n]["usd"] for n in names]
    lines = ["#!/bin/bash", "I=/data/harvest/code_l8x_assets_dev/tools/l8x_assets/isaac.sh"]
    for k in range(0, len(usds), BATCH):
        lines.append(f"bash $I {code} {gpu} xn_art{k // BATCH} tools.l8x_assets.gate_articulated --out {out} "
                     f"--assets {','.join(usds[k:k + BATCH])}")
    lines.append("echo CHAIN_DONE")
    open(chain, "w", newline="\n").write("\n".join(lines) + "\n")
    print(len(names), "assets,", (len(usds) + BATCH - 1) // BATCH, "processes")


if __name__ == "__main__":
    main()
