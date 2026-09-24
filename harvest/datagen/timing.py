"""R2 30 Hz grid on the 10 ms physics step (canon §37 sim.dt 0.01, §62 our data = 30 Hz). Pure.

100 Hz physics does not divide into 30 Hz, so tick k sits on physics substep n_k = round(100 k / 30) = (10 k + 1) // 3
(the fractional part of 10k/3 is 0, 1/3 or 2/3, never 1/2 -> no rounding ties). The command sent at tick k is held
for n_{k+1} - n_k = 3, 4, 3, 3, 4, 3, ... substeps (30 / 40 / 30 ms), so every 3 ticks = exactly 100 ms and the tick
time t_k = n_k * 10 ms is off the ideal k/30 s by 0 or +-3.33 ms (never accumulating). The recorded frame k is the
state at t_k (images rendered at t_k), action k is what was applied on [t_k, t_{k+1}).
Decision frames: every DEC_EVERY = 10 ticks (0.333 s nominal; actual intervals 0.33 / 0.34 / 0.33 s, T_c = 0.33 s).
"""
from __future__ import annotations

import numpy as np

PHYS_DT = 0.01
HZ = 30
DEC_EVERY = 10
H_DEFAULT = 15  # 0.5 s chunk (R4 contract)


def tick_sub(k: int) -> int:
    """Physics substep index of 30 Hz tick k (round(100 k / 30))."""
    return (10 * int(k) + 1) // 3


def hold_substeps(k: int) -> int:
    """Physics substeps the command of tick k is held for (3 or 4)."""
    return tick_sub(k + 1) - tick_sub(k)


def tick_time(k: int) -> float:
    return tick_sub(k) * PHYS_DT


def is_decision(k: int) -> bool:
    return int(k) % DEC_EVERY == 0


def chunk(actions, k: int, H: int = H_DEFAULT):
    """([H][8] action chunk starting at tick k, valid mask [H]): steps past the last recorded action repeat it
    and are masked 0 (padding only at the end, first step always real)."""
    a = np.asarray(actions, np.float32)
    n = len(a)
    if not 0 <= k < n:
        raise ValueError(f"chunk start {k} outside the {n} recorded actions")
    idx = [min(k + i, n - 1) for i in range(H)]
    return a[idx], [1 if k + i < n else 0 for i in range(H)]
