"""Placement feasibility per definition (pure): share of seeds whose handle path fits the arm box, and which bound
fails most. python tools/l9art/place_rate.py [n]"""
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9art import fixtures as FX  # noqa: E402
from harvest.l9art import scene_art as SA  # noqa: E402
from harvest.l9art import tasks as TK  # noqa: E402

OBJS = {"o1": {"name": "box", "fp": (0.06, 0.05), "h": 0.06}}
n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
for did, d in sorted(TK.DEFS.items()):
    for arm in ("right", "left"):
        ok, why = 0, Counter()
        for s in range(n):
            spec = FX.sample(d["family"], s) if d["family"] != "none" else None
            try:
                prog = TK.instantiate(did, spec, s, "box")
                SA.build(s, "ffw_sg2", arm, spec, prog, OBJS)
                ok += 1
            except ValueError as e:
                why[str(e)[:40]] += 1
                if spec is not None and "workspace" in str(e):
                    rng = np.random.default_rng(s)
                    fx = SA.place_fixture(spec, prog, arm, 0.77, rng)
                    P = SA.path_points(spec, prog, np.asarray(fx["T"]))
                    y = P[:, 1] * SA.side(arm)
                    for k, bad in (("x<", P[:, 0].min() < SA.WS_X[0]), ("x>", P[:, 0].max() > SA.WS_X[1]),
                                   ("y<", y.min() < SA.WS_Y[0]), ("y>", y.max() > SA.WS_Y[1]),
                                   ("z<", P[:, 2].min() < 0.77 + SA.WS_DZ[0]), ("z>", P[:, 2].max() > 0.77 + SA.WS_DZ[1])):
                        if bad:
                            why[k] += 1
        print(f"{did:20s} {arm:5s} ok {ok}/{n}  {dict(why.most_common(5))}")
