"""Print the prim tree of a USD (type, path; optional name filter) (pylib pxr).
usage: python tools/l8x_assets/usd_tree.py FILE [SUBSTRING]"""
from __future__ import annotations

import sys


def main(argv=None):
    from pxr import Usd, UsdPhysics
    a = argv or sys.argv[1:]
    st = Usd.Stage.Open(a[0])
    for p in st.Traverse():
        if len(a) > 1 and a[1] not in str(p.GetPath()):
            continue
        tags = [t for t, api in (("RB", UsdPhysics.RigidBodyAPI), ("COL", UsdPhysics.CollisionAPI)) if p.HasAPI(api)]
        print(p.GetTypeName() or "-", str(p.GetPath()), " ".join(tags))


if __name__ == "__main__":
    main()
