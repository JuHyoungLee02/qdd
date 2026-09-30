"""Deliberate failures / disturbances of a JCR data episode (docs/stage3/jcr_design.md §0-1, §0-2; NOW.md §1-0d).
Pure: plan_episode(seed, scale) decides everything from the seed (reproducible); the Isaac recorder applies it.
  normal (>= half of the episodes, P_NORMAL): no physical disturbance, no mid-command swap (upper-like command noise and
          delay still apply when the command source is 'upper')
  disturbed: one or two physical events from push (target shifted on approach), shake (target jittered right before the
          close), obstacle (an object appears beside the carry path, as P2), slip (gripper briefly opens while
          carrying) + command swaps (a command's noise is redrawn mid-move) at P_SWAP per command
Command source per episode: truth (clean, the ceiling's commands) with P_TRUTH, else upper (empirical 35B errors)."""
from __future__ import annotations

import numpy as np

P_NORMAL = 0.5
P_TRUTH = 0.3
P_SWAP = 0.10
P_PRE = 0.30
PHYS = ("push", "shake", "obstacle", "slip")


def plan_episode(seed: int, scale: float = 1.0) -> dict:
    rng = np.random.default_rng([int(seed), 7001])
    normal = bool(rng.uniform() < P_NORMAL)
    src = "truth" if rng.uniform() < P_TRUTH else "upper"
    n_ev = int(rng.integers(1, 3))
    kinds = [PHYS[i] for i in rng.choice(len(PHYS), size=n_ev, replace=False)]
    push_m = float(rng.uniform(0.01, 0.03)) * scale
    push_ang = float(rng.uniform(0, 2 * np.pi))
    shake_m = float(rng.uniform(0.005, 0.01)) * scale
    slip_m = float(rng.uniform(0.006, 0.010))
    slip_s = float(rng.uniform(0.2, 0.4))
    ev = []
    if not normal:
        for k in kinds:
            if k == "push":
                ev.append({"kind": "push", "dxy": [push_m * float(np.cos(push_ang)), push_m * float(np.sin(push_ang))],
                           "near_m": 0.06})
            elif k == "shake":
                ev.append({"kind": "shake", "amp_m": shake_m, "n": 3, "every_s": 0.15})
            elif k == "obstacle":
                ev.append({"kind": "obstacle"})
            else:
                ev.append({"kind": "slip", "open_m": slip_m, "dur_s": slip_s, "after_lift_s": 1.0})
    return {"seed": int(seed), "normal": normal, "src": src, "scale": float(scale), "events": ev,
            "p_swap": 0.0 if normal else P_SWAP, "p_pre": P_PRE, "rng_seed": [int(seed), 7002]}
