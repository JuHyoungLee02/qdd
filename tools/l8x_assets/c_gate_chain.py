"""Truth-gate chain for put-in task C on the flapless low boxes (boxes_noflap.json; coordinator 09-29): feasible
boxes by art_chain's C rule, gate seeds round-robin over them, one Isaac process per box, clean.
usage: python tools/l8x_assets/c_gate_chain.py NOFLAP.json CODE OUT CHAIN_PREFIX LANE[,LANE...] SEED0 N [N_FIX]"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from tools.l8x_assets import art_chain as AC  # noqa: E402


def main(argv=None):
    a = argv or sys.argv[1:]
    boxes = {n: r for n, r in json.load(open(a[0])).items() if r.get("ok", True) and "error" not in r}
    code, out, prefix, lanes = a[1], a[2], a[3], a[4].split(",")
    seeds = list(range(int(a[5]), int(a[5]) + int(a[6])))
    AC.N_FIX = int(a[7]) if len(a) > 7 else 5
    fx = AC.feasible(boxes, {n: {"task": "C"} for n in boxes}, "C")
    print("C", fx)
    O = a[0] if a[0].startswith("/data/") else "/data/harvest/assets_x/boxes_noflap.json"
    by = {f: [] for f in fx}
    for i, s in enumerate(seeds):
        by[fx[i % len(fx)]].append(s)
    lines = {g: [] for g in lanes}
    for i, (f, ss) in enumerate(by.items()):
        g = lanes[i % len(lanes)]
        lines[g].append(f"bash $I {code} {g.split(':')[-1]} xn_cgate_{f} tools.l8x_assets.run_art --kind C --fixture {f} "
                        f"--opened {O} --objects /data/harvest/out/l8x_assets/art_targets.json "
                        f"--seeds {','.join(map(str, ss))} --split gate --clean --video-seeds {ss[0]} --out {out}")
    for g, ls in lines.items():
        p = f"{prefix}_{g.replace(':', '_')}.sh"
        open(p, "w", newline="\n").write("\n".join(["#!/bin/bash", "I=/data/harvest/code_l8x_assets_dev/tools/"
                                                    "l8x_assets/isaac.sh"] + ls + ["echo CHAIN_DONE"]) + "\n")
        print(p, len(ls))


if __name__ == "__main__":
    main()
