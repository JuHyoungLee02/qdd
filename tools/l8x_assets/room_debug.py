"""Occupancy stats of an iTHOR scene (pod, pxr): floor z, open fraction, largest clear rectangle; saves the open map
as .npy (x, y) for a look.
usage: python tools/l8x_assets/room_debug.py scene.usda OUT.npy"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import rooms as RO  # noqa: E402
from harvest.sim.assets_x import surfaces as S  # noqa: E402
from harvest.sim.assets_x.usd_import import collider_mesh, render_mesh  # noqa: E402


def main(argv=None):
    from pxr import Usd
    a = argv or sys.argv[1:]
    st0 = Usd.Stage.Open(a[0])
    P, F = collider_mesh(st0, exact_mesh=True)
    Rm = render_mesh(st0)
    print("points", P.shape, "bbox", P.min(0).round(2), P.max(0).round(2))
    x0, y0, nx, ny, open_, fz = RO.occupancy(P, F, Rm)
    print("floor z", round(fz, 3), "grid", nx, ny, "open frac", round(float(open_.mean()), 3))
    r = S.max_rect(open_)
    if r:
        print("max rect m", (r[1] - r[0] + 1) * S.RES, (r[3] - r[2] + 1) * S.RES)
    np.save(a[1], open_)
    from pxr import UsdGeom, UsdPhysics
    xc = UsdGeom.XformCache()
    big = []
    st = Usd.Stage.Open(a[0])
    for p in st.Traverse(Usd.TraverseInstanceProxies()):
        if p.HasAPI(UsdPhysics.CollisionAPI) and p.GetTypeName() in ("Cube", "Mesh"):
            b = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "guide", "proxy"]).ComputeWorldBound(p)
            r = b.ComputeAlignedRange()
            lo, hi = np.array(r.GetMin()), np.array(r.GetMax())
            big.append(((hi[0] - lo[0]) * (hi[1] - lo[1]), str(p.GetPath())[-60:], p.GetTypeName(),
                        lo.round(2).tolist(), hi.round(2).tolist()))
    for row in sorted(big, reverse=True)[:10]:
        print(row)
    del xc


if __name__ == "__main__":
    main()
