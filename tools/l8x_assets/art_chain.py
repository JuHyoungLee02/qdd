"""Chain scripts for the articulated put-in tasks A / C (xart; user-log 185): feasible fixtures from the baked opened
copies (A: train drawer pieces whose top is <= 0.22 m above the open drawer's floor -- the executor box; C: boxes
with an open inside, rim <= 0.28 m), seeds round-robin over the fixtures, one Isaac process per (task, fixture);
gate seeds clean. Lanes = GPUs.
usage: python tools/l8x_assets/art_chain.py OPENED.json SPEC.json CODE OUT CHAIN_PREFIX GPU[,GPU...] [HOST_PREFIXES]"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.teach_l8d import xart as XA  # noqa: E402

SEEDS = {"A": (range(49150, 49160), range(35490, 35494)), "C": (range(49170, 49180), range(35496, 35500))}
TOP_GAP_MAX, RIM_MAX = 0.17, 0.28  # pilot: Desk_308_2_1 (0.205) blocked carrying to the drawer near the body
N_FIX = 4


def feasible(opened: dict, spec: dict, kind: str) -> list:
    out = []
    for n, r in sorted(opened.items()):
        if "error" in r or spec.get(n, {}).get("task") != kind or spec[n].get("split", "train") != "train":
            continue
        ts = XA.target_surface(r, kind)
        if ts is None:
            continue
        if kind == "A":
            top = XA.top_surface(r)
            if top is None or top["top_z"] - ts["top_z"] > TOP_GAP_MAX:
                continue
        elif ts.get("rim_z") is None or ts["rim_z"] - ts["top_z"] > RIM_MAX or ts["area"] < 0.03:
            continue
        out.append((ts["area"], n))
    return [n for _, n in sorted(out, reverse=True)[:N_FIX]]


def main(argv=None):
    a = argv or sys.argv[1:]
    opened, spec = json.load(open(a[0])), json.load(open(a[1]))
    code, out, prefix = a[2], a[3], a[4]
    gpus = a[5].split(",")  # lanes "name:gpu" (a pod and its card) or plain gpu ids
    O, T = "/data/harvest/out/l8x_assets/art_open/opened.json", "/data/harvest/out/l8x_assets/art_targets.json"
    jobs = []
    for kind, (train, gate) in SEEDS.items():
        fx = feasible(opened, spec, kind)
        print(kind, fx)
        for split, seeds in (("gate", gate), ("train", train)):
            by = {f: [] for f in fx}
            for i, s in enumerate(seeds):
                by[fx[i % len(fx)]].append(s)
            for f, ss in by.items():
                if ss:
                    jobs.append((kind, f, split, ss))
    lanes = {g: [] for g in gpus}
    for i, (kind, f, split, ss) in enumerate(jobs):
        g = gpus[i % len(gpus)]
        gi = g.split(":")[-1]
        tag = f"xn_art_{kind}_{split}_{f}"
        clean = " --clean" if split == "gate" else ""
        lanes[g].append(f"bash $I {code} {gi} {tag} tools.l8x_assets.run_art --kind {kind} --fixture {f} --opened {O} "
                        f"--objects {T} --seeds {','.join(map(str, ss))} --split {split}{clean} "
                        f"--video-seeds {ss[0]} --out {out}")
    for g, lines in lanes.items():
        p = f"{prefix}_{g.replace(':', '_')}.sh"
        open(p, "w", newline="\n").write("\n".join(["#!/bin/bash", "I=/data/harvest/code_l8x_assets_dev/tools/"
                                                    "l8x_assets/isaac.sh"] + lines + ["echo CHAIN_DONE"]) + "\n")
        print(p, len(lines))


if __name__ == "__main__":
    main()
