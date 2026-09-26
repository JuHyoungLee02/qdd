"""Print stage metadata, prim type counts, collision / rigid-body API counts and the render bbox of USD files (pxr).
usage: python tools/l8x_assets/inspect_usd.py FILE.usd [...]"""
from __future__ import annotations

import sys


def main(argv=None):
    from pxr import Usd, UsdGeom, UsdPhysics
    for f in argv or sys.argv[1:]:
        st = Usd.Stage.Open(f)
        types, col, rb = {}, 0, 0
        for p in st.Traverse(Usd.TraverseInstanceProxies()):
            types[p.GetTypeName()] = types.get(p.GetTypeName(), 0) + 1
            col += p.HasAPI(UsdPhysics.CollisionAPI)
            rb += p.HasAPI(UsdPhysics.RigidBodyAPI)
        bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(st.GetPseudoRoot())
        r = bb.ComputeAlignedRange()
        dp = st.GetDefaultPrim()
        print(f, "| up", UsdGeom.GetStageUpAxis(st), "| mpu", UsdGeom.GetStageMetersPerUnit(st),
              "| default", dp.GetPath() if dp else None, "| colliders", col, "| rigid", rb,
              "| bbox min", tuple(round(v, 3) for v in r.GetMin()), "max", tuple(round(v, 3) for v in r.GetMax()),
              "| types", dict(sorted(types.items(), key=lambda kv: -kv[1])[:6]))


if __name__ == "__main__":
    main()
