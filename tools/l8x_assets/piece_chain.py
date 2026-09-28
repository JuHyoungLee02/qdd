"""Write the per-piece furniture gate chain (gate_pieces.py) for b4: train pieces of the tables / counters / shelves
(dressers, shelving units, TV stands) / side and low tables of assets_table.json, at most CAP per THOR family (the
name without its numeric suffix), picked by name hash (deterministic); one Isaac process per (kind, batch).
usage: python tools/l8x_assets/piece_chain.py CODE_DIR GPU OUT_DIR CHAIN.sh [LANES]"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

KINDS = ("thor_table", "thor_counter", "thor_shelf", "thor_side_table", "thor_low_table")
CAP = {"Desk": 8, "Dining_Table": 8, "Dresser": 8, "Shelving_Unit": 6, "TV_Stand": 6, "Side_Table": 6,
       "Coffee_Table": 5, "Cabinet_Straight": 2, "Cabinet_Corner": 1, "IKEACabinet": 1}
COUNTER_CAP = 10  # the Countertop_* families have one piece each: 10 of them in total
BATCH = 8


def family(n: str) -> str:
    return re.sub(r"(_\d+)+$", "", n)


def candidates(table: dict) -> dict:
    by = {}
    for n, a in sorted(table.items()):
        k = a.get("tag", "thor") + "_" + a["category"]
        if a["split"] != "train" or k not in KINDS:
            continue
        by.setdefault(k, {}).setdefault(family(n), []).append(n)
    out = {}
    for k, fams in by.items():
        pick, counters = [], []
        for f, names in sorted(fams.items()):
            names = sorted(names, key=lambda n: hashlib.sha256(f"b4-piece:{n}".encode()).hexdigest())
            if f.startswith("Countertop"):
                counters += names
            else:
                pick += names[:CAP.get(f, 2)]
        counters.sort(key=lambda n: hashlib.sha256(f"b4-piece:{n}".encode()).hexdigest())
        out[k] = pick + counters[:COUNTER_CAP]
    return out


def main(argv=None):
    a = argv or sys.argv[1:]
    code, gpu, out, chain = a[0], a[1], a[2], a[3]
    lanes = int(a[4]) if len(a) > 4 else 1
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    table = json.load(open(os.path.join(root, "harvest", "sim", "assets_x", "assets_table.json")))["assets"]
    cand = candidates(table)
    jobs = []
    for k, names in sorted(cand.items()):
        for i in range(0, len(names), BATCH):
            jobs.append((k, names[i:i + BATCH]))
    for lane in range(lanes):
        lines = ["#!/bin/bash", "I=/data/harvest/code_l8x_assets_dev/tools/l8x_assets/isaac.sh"]
        for j, (k, names) in enumerate(jobs):
            if j % lanes == lane:
                lines.append(f"bash $I {code} {gpu} xn_pc{lane}_{j} tools.l8x_assets.gate_pieces --kind {k} "
                             f"--pieces {','.join(names)} --out {out}")
        lines.append("echo CHAIN_DONE")
        p = chain.replace(".sh", f"_{lane}.sh")
        open(p, "w", newline="\n").write("\n".join(lines) + "\n")
    print({k: len(v) for k, v in cand.items()}, "pieces", sum(len(v) for v in cand.values()), "jobs", len(jobs))


if __name__ == "__main__":
    main()
