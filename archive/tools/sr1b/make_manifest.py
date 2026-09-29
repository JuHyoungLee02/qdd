"""E-SR1b: the verdict manifest from the lane outputs (docs/stage3/prereg_sr1b.md §6).
  python tools/sr1b/make_manifest.py <log dir> <w grid, e.g. 1,1.5,2,3,5,8>  > manifest.json
Baseline = C0 seeds 0 (the E-MA2 C0 checkpoint) and 1 at w = 1; arms A / AB / A02 on the grid, B at w = 1;
A / B / AB / C0 two seeds, A02 one seed. Every listed file must exist."""
from __future__ import annotations

import json
import os
import sys

ARMS = {"A": ((0, 1), True), "B": ((0, 1), False), "AB": ((0, 1), True), "A02": ((0,), True)}


def tag(w: str) -> str:
    return f"{float(w):g}"


def manifest(log: str, grid: str) -> dict:
    ws = [tag(w) for w in grid.split(",")]
    f = lambda arm, s, w: os.path.join(log, f"ev_{arm}_s{s}_w{w}.jsonl")  # noqa: E731
    out = {"baseline": [f("C0", s, "1") for s in (0, 1)], "arms": {}}
    for arm, (seeds, cfg) in ARMS.items():
        out["arms"][arm] = {w: [f(arm, s, w) for s in seeds] for w in (ws if cfg else ["1"])}
    miss = [p for p in out["baseline"] + [p for a in out["arms"].values() for ps in a.values() for p in ps]
            if not os.path.exists(p)]
    if miss:
        raise SystemExit(f"missing: {miss}")
    return out


if __name__ == "__main__":
    print(json.dumps(manifest(sys.argv[1], sys.argv[2]), indent=1))
