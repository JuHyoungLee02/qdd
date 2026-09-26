"""Licensed mesh furniture -> static USD + support surfaces (pxr only, no Isaac; pod: usd-core in
/data/harvest/assets_x/pylib).

MolmoSpaces THOR assets (CC BY 4.0) come as articulated rigid bodies (doors / drawers on joints, mass 1e-8 roots,
primitive colliders with purpose "guide"). For a static furniture piece we
  1. flatten the asset stage and write <name>_static.usda NEXT TO the original (relative texture paths stay valid);
  2. strip every rigid-body / articulation / mass / filtered-pairs API and deactivate every joint -> the primitive
     colliders become static colliders of one fixed piece (doors frozen closed);
  3. read the world-space primitive colliders (Cube / Capsule / Sphere / Cylinder as their boxes) and extract the
     support surfaces from them (surfaces.mesh_support_surfaces) -- the collision geometry is what an object stands
     on, so surfaces come from it, not from the render mesh;
  4. THOR geometry is Y-up although the layer says Z: a wrapper /Piece/norm/yup (rotateX 90, as MolmoSpaces
     viewer.FIX_ASSETS_ROTATION does);
  5. normalise the pose: the piece's collider bbox bottom-centre goes to the origin (spawn at (x, y, 0) = on the
     floor), up axis must be Z and metersPerUnit 1 (checked, else refused).
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

from . import surfaces as S

STRIP_APIS = ("PhysicsRigidBodyAPI", "PhysicsArticulationRootAPI", "PhysicsMassAPI", "PhysicsFilteredPairsAPI",
              "PhysxArticulationAPI", "PhysxRigidBodyAPI")
COLLIDER_TYPES = ("Cube", "Capsule", "Sphere", "Cylinder", "Mesh")


def _xf_cache():
    from pxr import Usd, UsdGeom
    return UsdGeom.XformCache(Usd.TimeCode.Default())


def _world_corners(prim, xc):
    """8 world corners of a collider prim's local box (Cube size, Capsule / Cylinder radius+height+axis, Sphere,
    Mesh extent)."""
    from pxr import UsdGeom
    t = prim.GetTypeName()
    if t == "Cube":
        h = float(UsdGeom.Cube(prim).GetSizeAttr().Get()) / 2
        lo, hi = np.array([-h] * 3), np.array([h] * 3)
    elif t == "Sphere":
        r = float(UsdGeom.Sphere(prim).GetRadiusAttr().Get())
        lo, hi = np.array([-r] * 3), np.array([r] * 3)
    elif t in ("Capsule", "Cylinder"):
        g = UsdGeom.Capsule(prim) if t == "Capsule" else UsdGeom.Cylinder(prim)
        r, hh = float(g.GetRadiusAttr().Get()), float(g.GetHeightAttr().Get()) / 2
        ax = str(g.GetAxisAttr().Get() or "Z")
        ext = {"X": [hh + (r if t == "Capsule" else 0), r, r], "Y": [r, hh + (r if t == "Capsule" else 0), r],
               "Z": [r, r, hh + (r if t == "Capsule" else 0)]}[ax]
        lo, hi = -np.array(ext), np.array(ext)
    else:  # Mesh collider: its local extent
        pts = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), float)
        lo, hi = pts.min(0), pts.max(0)
    M = np.asarray(xc.GetLocalToWorldTransform(prim), float)  # row-vector convention: p_w = [p 1] M
    C = np.array([[x, y, z, 1.0] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    W = C @ M
    return W[:, :3]


_BOX_ORDER = [0, 4, 6, 2, 1, 5, 7, 3]  # _world_corners order (x, y, z nested) -> surfaces.box_mesh vertex order


def collider_boxes(stage):
    """[(prim path, 8 world corners)] of every collision-enabled prim (static or not) that is not a joint."""
    from pxr import Usd, UsdPhysics
    xc = _xf_cache()
    out = []
    for p in stage.Traverse(Usd.TraverseInstanceProxies()):
        if p.GetTypeName() in COLLIDER_TYPES and p.HasAPI(UsdPhysics.CollisionAPI):
            en = p.GetAttribute("physics:collisionEnabled")
            if en and en.Get() is False:
                continue
            out.append((str(p.GetPath()), _world_corners(p, xc)))
    return out


def boxes_mesh(boxes):
    """Oriented boxes (8 corners each) -> one triangle mesh (surfaces.box_mesh faces on reordered corners)."""
    _, F = S.box_mesh((0, 0, 0), (1, 1, 1))
    meshes = []
    for _, c in boxes:
        P = np.asarray(c, float)[_BOX_ORDER]
        meshes.append((P, F))
    return S.merge_meshes(meshes)



def _mesh_world(prim, xc):
    """A Mesh prim as world-space triangles (fan triangulation of each face)."""
    from pxr import UsdGeom
    m = UsdGeom.Mesh(prim)
    pts = np.asarray(m.GetPointsAttr().Get(), float)
    cnt = np.asarray(m.GetFaceVertexCountsAttr().Get(), int)
    idx = np.asarray(m.GetFaceVertexIndicesAttr().Get(), int)
    M = np.asarray(xc.GetLocalToWorldTransform(prim), float)
    W = (np.c_[pts, np.ones(len(pts))] @ M)[:, :3]
    F, k = [], 0
    for c in cnt:
        f = idx[k:k + c]
        F += [[f[0], f[i], f[i + 1]] for i in range(1, c - 1)]
        k += c
    F = np.asarray(F, int).reshape(-1, 3)
    if str(m.GetOrientationAttr().Get()) == "leftHanded" or np.linalg.det(M[:3, :3]) < 0:
        F = F[:, ::-1]
    return W, F


def render_mesh(stage):
    """Every render Mesh prim (purpose default / render) as one world-space triangle mesh."""
    from pxr import Usd, UsdGeom
    xc = _xf_cache()
    parts = []
    for p in stage.Traverse(Usd.TraverseInstanceProxies()):
        if p.GetTypeName() == "Mesh" and UsdGeom.Imageable(p).ComputePurpose() in ("default", "render"):
            W, F = _mesh_world(p, xc)
            if len(F):
                parts.append((W, F))
    return S.merge_meshes(parts)


def collider_mesh(stage, exact_mesh: bool = False):
    """All colliders as one triangle mesh: primitives as their boxes; Mesh colliders as their boxes, or with
    exact_mesh as their own triangles (cyclo_lab tables have one mesh collider for the whole table)."""
    from pxr import Usd, UsdPhysics
    if not exact_mesh:
        return boxes_mesh(collider_boxes(stage))
    xc = _xf_cache()
    parts, boxes = [], []
    for p in stage.Traverse(Usd.TraverseInstanceProxies()):
        if p.GetTypeName() in COLLIDER_TYPES and p.HasAPI(UsdPhysics.CollisionAPI):
            en = p.GetAttribute("physics:collisionEnabled")
            if en and en.Get() is False:
                continue
            if p.GetTypeName() == "Mesh":
                parts.append(_mesh_world(p, xc))
            else:
                boxes.append((str(p.GetPath()), _world_corners(p, xc)))
    if boxes:
        parts.append(boxes_mesh(boxes))
    if not parts:
        raise ValueError("no colliders")
    return S.merge_meshes(parts)

def render_bbox(stage):
    from pxr import Usd, UsdGeom
    bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(stage.GetPseudoRoot())
    r = bb.ComputeAlignedRange()
    return np.array(r.GetMin(), float), np.array(r.GetMax(), float)


def make_static(src: str, dst: str | None = None, y_up_fix: bool = True, mode: str = "thor") -> dict:
    """Write the static, flattened copy next to src -> {dst, stripped, joints, meters_per_unit, up_axis}.
    mode "thor": the layer must say metersPerUnit 1 / upAxis Z and y_up_fix applies (THOR geometry is Y-up).
    mode "declared" (cyclo_lab): trust the declared up axis (Y -> rotateX 90) and take the coordinates as metres
    whatever metersPerUnit says (cyclo_lab spawns these files unscaled; their numbers are metres: a 0.75 table),
    and the flat copy is re-labelled metersPerUnit 1 / upAxis Z so no metrics correction can apply on load."""
    from pxr import Sdf, Usd, UsdGeom
    stage = Usd.Stage.Open(src)
    mpu, up = float(UsdGeom.GetStageMetersPerUnit(stage)), str(UsdGeom.GetStageUpAxis(stage))
    if mode == "thor" and (abs(mpu - 1.0) > 1e-9 or up != "Z"):
        raise ValueError(f"{src}: metersPerUnit {mpu} upAxis {up} (only 1 / Z accepted)")
    if mode == "declared":
        y_up_fix = up == "Y"
    elif mode != "thor":
        raise ValueError(mode)
    layer = stage.Flatten()
    dst = dst or os.path.splitext(src)[0] + "_static.usda"
    stripped, joints = 0, 0

    def visit(spec):
        nonlocal stripped, joints
        info = spec.GetInfo("apiSchemas") if spec.HasInfo("apiSchemas") else None
        if info is not None:
            items = [a for a in info.GetAddedOrExplicitItems() if a not in STRIP_APIS]
            n_before = len(info.GetAddedOrExplicitItems())
            lo = Sdf.TokenListOp()
            lo.prependedItems = items
            spec.SetInfo("apiSchemas", lo)
            stripped += n_before - len(items)
        if "Joint" in spec.typeName:
            spec.active = False
            joints += 1
        for c in spec.nameChildren:
            visit(c)

    for root in layer.rootPrims:
        visit(root)
    layer.pseudoRoot.SetInfo("metersPerUnit", 1.0)
    layer.pseudoRoot.SetInfo("upAxis", "Z")
    flat = os.path.splitext(dst)[0] + "_flat.usda"
    layer.Export(flat)
    # wrapper: /Piece (free for the spawner's translate / orient) / norm (translate: collider bbox bottom-centre
    # to the origin) / yup (rotateX 90: THOR geometry is Y-up although the layer says Z -- MolmoSpaces
    # viewer.FIX_ASSETS_ROTATION) -> reference to the flattened static layer. v2 put the rotation as an op on the
    # asset root: Isaac Lab's spawner rewrote that prim's xformOpOrder and the piece vanished from its place.
    if os.path.exists(dst):
        os.remove(dst)
    st = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(st, "/Piece")
    st.SetDefaultPrim(root.GetPrim())
    norm = UsdGeom.Xform.Define(st, "/Piece/norm")
    yup = UsdGeom.Xform.Define(st, "/Piece/norm/yup")
    if y_up_fix:
        yup.AddRotateXOp().Set(90.0)
    yup.GetPrim().GetReferences().AddReference(os.path.basename(flat))
    lo, hi = _collider_range(st, exact_mesh=mode == "declared")
    tr = norm.AddTranslateOp()
    tr.Set((-float((lo[0] + hi[0]) / 2), -float((lo[1] + hi[1]) / 2), -float(lo[2])))
    st.GetRootLayer().Save()
    return {"dst": dst, "flat": flat, "stripped_apis": stripped, "joints_deactivated": joints,
            "meters_per_unit": mpu, "up_axis": up, "y_up_fix": bool(y_up_fix),
            "raw_origin": [round(float(v), 4) for v in ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])]}


VISUAL_STRIP = STRIP_APIS + ("PhysicsCollisionAPI", "PhysicsMeshCollisionAPI", "PhysxCollisionAPI",
                             "PhysxConvexHullCollisionAPI", "PhysxConvexDecompositionCollisionAPI",
                             "PhysxSDFMeshCollisionAPI", "PhysicsMaterialAPI")


def make_visual(src: str, dst: str | None = None, ext: str = ".usda") -> dict:
    """A render-only flattened copy next to src (no rigid body, collider, joint or physics scene): the mesh a
    spawner can reference under its own collider (randomize.spawn_rd style, up = "Y" for MolmoSpaces)."""
    from pxr import Sdf, Usd
    layer = Usd.Stage.Open(src).Flatten()
    dst = dst or os.path.splitext(src)[0] + "_visual" + ext
    n = 0

    def visit(spec):
        nonlocal n
        if spec.typeName == "PhysicsScene" or "Joint" in spec.typeName:
            spec.active = False
        if spec.HasInfo("apiSchemas"):
            info = spec.GetInfo("apiSchemas")
            items = [x for x in info.GetAddedOrExplicitItems() if x not in VISUAL_STRIP]
            n += len(info.GetAddedOrExplicitItems()) - len(items)
            lo = Sdf.TokenListOp()
            lo.prependedItems = items
            spec.SetInfo("apiSchemas", lo)
        for c in spec.nameChildren:
            visit(c)

    for root in layer.rootPrims:
        visit(root)
    layer.Export(dst)
    return {"visual": dst, "stripped_apis": n}


def _collider_range(stage, exact_mesh: bool = False):
    P, _ = collider_mesh(stage, exact_mesh)
    return P.min(0), P.max(0)


def inspect(src_static: str, exact_mesh: bool = False) -> dict:
    """Static copy -> {bbox (render), collider bbox, n_colliders, surfaces (asset frame, origin = collider bbox
    bottom-centre)}."""
    from pxr import Usd
    stage = Usd.Stage.Open(src_static)
    boxes = collider_boxes(stage)
    if not boxes:
        raise ValueError(f"{src_static}: no colliders")
    P, F = collider_mesh(stage, exact_mesh)
    lo, hi = P.min(0), P.max(0)
    origin = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    P0 = P - origin
    rlo, rhi = render_bbox(stage)
    surfs = S.mesh_support_surfaces(P0, F)
    return {"n_colliders": len(boxes), "origin_offset": [round(float(v), 4) for v in origin],
            "collider_size": [round(float(v), 4) for v in hi - lo],
            "render_size": [round(float(v), 4) for v in rhi - rlo],
            "render_vs_collider_mm": round(float(np.abs((rhi - rlo) - (hi - lo)).max() * 1e3), 1),
            "surfaces": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()} for s in surfs]}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="static copy + surfaces of licensed furniture USDs")
    ap.add_argument("usd", nargs="+")
    ap.add_argument("--out", required=True, help="json table (one row per asset)")
    ap.add_argument("--mode", default="thor", choices=("thor", "declared"))
    a = ap.parse_args(argv)
    rows = {}
    for src in a.usd:
        name = os.path.splitext(os.path.basename(src))[0]
        try:
            st = make_static(src, mode=a.mode)
            rows[name] = dict(src=src, **st, **inspect(st["dst"], exact_mesh=a.mode == "declared"))
        except Exception as e:  # noqa: BLE001 - recorded per asset, the table keeps going
            rows[name] = {"src": src, "error": f"{type(e).__name__}: {e}"}
        r = rows[name]
        print(name, r.get("collider_size"), len(r.get("surfaces", [])), r.get("error", ""), flush=True)
    with open(a.out, "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()

assert math.isclose(len(_BOX_ORDER), 8)
