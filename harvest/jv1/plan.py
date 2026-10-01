"""E-JV1 disturbed evaluation set (docs/stage3/prereg_jv1.md §4): the d1 physical disturbance kinds (push / shake /
obstacle / slip, harvest.jcr.disturb) with the d1 magnitudes (scale 0.75), but always disturbed and on the DEV layout
seeds 0-19 with its own random stream ([seed, variant, 7101]) -- fixed before any result, identical for every arm."""
from __future__ import annotations

import numpy as np

from ..jcr import disturb as D

SCALE = 0.75  # = d1 (prereg_jcr1 'start d1')


def disturbed_events(seed: int, variant: str, scale: float = SCALE) -> list:
    rng = np.random.default_rng([int(seed), 0 if variant == "standard" else 1, 7101])
    n_ev = int(rng.integers(1, 3))
    kinds = [D.PHYS[i] for i in rng.choice(len(D.PHYS), size=n_ev, replace=False)]
    push_m = float(rng.uniform(0.01, 0.03)) * scale
    push_ang = float(rng.uniform(0, 2 * np.pi))
    shake_m = float(rng.uniform(0.005, 0.01)) * scale
    slip_m = float(rng.uniform(0.006, 0.010))
    slip_s = float(rng.uniform(0.2, 0.4))
    ev = []
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
    return ev
