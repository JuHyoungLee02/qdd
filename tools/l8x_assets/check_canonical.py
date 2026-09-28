"""Check the canonical fields of real-object rows (pod, pxr): spawn each object at canonical pose (centre (0, 0, h/2),
identity) with objv.root_from_canonical, transform its render mesh by the root pose and compare the mesh bbox with
the expected canonical box (centre 0, extents 2 * half_extents). Prints the worst offsets.
usage: python tools/l8x_assets/check_canonical.py TABLE.json [ids...]"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim import objv  # noqa: E402
from harvest.sim.assets_x.usd_import import render_mesh  # noqa: E402


def main(argv=None):
    from pxr import Usd
    a = argv or sys.argv[1:]
    rows = json.load(open(a[0]))["objects"]
    ids = a[1:] or sorted(rows)[:8]
    for k in ids:
        r = rows[k]
        g = objv.geom(r)
        root, q = objv.root_from_canonical(g, np.array([0.0, 0.0, g["height"] / 2]), (1.0, 0.0, 0.0, 0.0))
        P, _ = render_mesh(Usd.Stage.Open(r["usd_physics"]))
        W = np.array([objv.qrot(tuple(q), p) for p in P[:: max(1, len(P) // 4000)]]) + root
        lo, hi = W.min(0), W.max(0)
        c, e = (lo + hi) / 2, hi - lo
        print(f"{k[:40]:40s} centre {np.round(c * 1000, 1)} mm (want 0,0,{g['height'] * 500:.1f}) extent "
              f"{np.round(e * 1000, 1)} want {np.round(np.array(g['half_extents']) * 2000, 1)}")


if __name__ == "__main__":
    main()
