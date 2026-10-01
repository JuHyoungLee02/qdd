"""(pod) Print link mesh AABBs in a frame at given joint values.
usage: probe_links.py <urdf> <frame> '<json q>' link [link...]"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from urdf_fk import Urdf  # noqa: E402

ZMAX = None
if sys.argv[1].startswith("zmax="):
    ZMAX = float(sys.argv.pop(1)[5:])
u = Urdf(sys.argv[1])
q = json.loads(sys.argv[3])
for k in sys.argv[4:]:
    for kind in ("visual", "collision"):
        try:
            p = u.link_points(k, sys.argv[2], q, kind)
        except Exception as e:  # noqa: BLE001
            print(k, kind, "ERR", e)
            continue
        if ZMAX is not None:
            p = p[p[:, 2] < ZMAX]
        if len(p):
            print(f"{k:28s} {kind:9s} n={len(p):6d} min {np.round(p.min(0), 4)} max {np.round(p.max(0), 4)}")
    T = u.T_rel(k, sys.argv[2], q)
    print(f"{'':28s} origin {np.round(T[:3, 3], 4)}")
