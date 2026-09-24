"""Seed splits and the R6 guard (E §1.5, plan e2e-ready R6).

DEV 0-29 and POOL 2000-2119 are free to use. CAL 500-549, TEST 1000-1149 and TEST-P5 1300-1329 are opened only by
an explicit `--split cal|test|test_p5` AND the environment variable HARVEST_ALLOW_SPLIT set to the same value. Only
the main session sets that variable, at the pre-registered time of the experiment that uses the split; no agent or
smoke run sets it. Every seed an evaluation touches is checked against the declared split, so a protected seed can
never be generated or opened by accident under dev / pool.
"""
from __future__ import annotations

import os

RANGES = {"dev": range(0, 30), "cal": range(500, 550), "test": range(1000, 1150), "test_p5": range(1300, 1330),
          "pool": range(2000, 2120)}
PROTECTED = ("cal", "test", "test_p5")
ENV = "HARVEST_ALLOW_SPLIT"


def split_of(seed: int) -> str | None:
    s = int(seed)
    for name, r in RANGES.items():
        if s in r:
            return name
    return None


def check_split(split: str, env=None) -> str:
    env = os.environ if env is None else env
    if split not in RANGES:
        raise SystemExit(f"--split {split!r}: one of {sorted(RANGES)}")
    if split in PROTECTED and env.get(ENV) != split:
        raise SystemExit(f"--split {split} refused: set {ENV}={split} (main session only, at the pre-registered "
                         f"time of the experiment; CAL 500-549 / TEST 1000-1149 / TEST-P5 1300-1329 stay closed)")
    return split


def check_seeds(seeds, split: str, env=None) -> list:
    check_split(split, env)
    out = [int(s) for s in seeds]
    bad = [s for s in out if split_of(s) != split]
    if bad:
        raise SystemExit(f"seeds {bad[:10]} are not in split {split} {RANGES[split]} (refused, never opened)")
    return out
