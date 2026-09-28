"""Print a USD's up axis, metersPerUnit, default prim, mesh count, render bbox and collider count (pylib pxr).
usage: python tools/l8x_assets/usd_probe.py FILE [FILE ...]"""
from __future__ import annotations

import sys


def main(argv=None):
    from pxr import Usd, UsdGeom, UsdPhysics
    for f in argv or sys.argv[1:]:
        st = Usd.Stage.Open(f)
        n_mesh = sum(p.GetTypeName() == "Mesh" for p in st.Traverse())
        n_col = sum(p.HasAPI(UsdPhysics.CollisionAPI) for p in st.Traverse())
        bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(st.GetPseudoRoot())
        r = bb.ComputeAlignedRange()
        print(f, "up", UsdGeom.GetStageUpAxis(st), "mpu", UsdGeom.GetStageMetersPerUnit(st),
              "default", st.GetDefaultPrim().GetPath() if st.GetDefaultPrim() else None, "meshes", n_mesh,
              "colliders", n_col, "size", [round(float(v), 3) for v in (r.GetMax() - r.GetMin())])


if __name__ == "__main__":
    main()
