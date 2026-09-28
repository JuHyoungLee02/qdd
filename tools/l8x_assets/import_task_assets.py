"""Assets of the diversified tasks (user-log 178; pod, pylib python: pxr + numpy + Pillow).

containers (harvest/sim/assets_x/containers.json): place targets with an inside -- baskets (GSO, CC BY 4.0; Poly
  Haven wicker baskets, CC0), pen holders (GSO utensil / toothbrush holders and mugs, CC BY 4.0) and blender jars
  (procedural, ours: open tapered jar on a motor base; no licensed blender asset in THOR / GSO / Poly Haven / the
  Objaverse subset). A container is a KINEMATIC body with a triangle-mesh collider (a convex hull would fill the
  inside); its inside comes from surfaces.mesh_support_surfaces (container = rim >= 3 cm above the floor): inner
  floor z, rim z, inner free box (the drop target) and the opening box (the free box grown to the rim wall,
  measured at the rim height), all in the container's canonical frame (bottom centre at the origin).
items (harvest/sim/assets_x/task_items.json, objv-compatible rows like objects_real): fruit scans (Poly Haven
  bananas / food_apple_01 / food_pears_asian_01 / lemon, CC0) and pens / pencils (THOR Pen_* / Pencil_*, CC BY 4.0;
  thin: grasp width 0.5-2 cm, own size box). THOR apples / tomatoes / potatoes are already objects_real rows.
usage: python tools/l8x_assets/import_task_assets.py --gso DIR --ph DIR --thor DIR --out-containers C.json
       --out-items I.json"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import objects_real as OR  # noqa: E402
from harvest.sim.assets_x import surfaces as SU  # noqa: E402
from harvest.sim.assets_x import usd_import as UI  # noqa: E402
from tools.l8x_assets import import_products as IP  # noqa: E402
from tools.l8x_assets import real_table as RT  # noqa: E402

GSO_CONTAINERS = {  # name -> role
    "Target_Basket_Medium": "basket",
    "Threshold_Basket_Natural_Finish_Fabric_Liner_Small": "basket",
    "Spritz_Easter_Basket_Plastic_Teal": "basket",
    "RJ_Rabbit_Easter_Basket_Blue": "basket",
    "Smith_Hawken_Woven_BasketTray_Organizer_with_3_Compartments_95_x_9_x_13": "basket",
    "BIA_Cordon_Bleu_White_Porcelain_Utensil_Holder_900028": "pen_holder",
    "Circo_Fish_Toothbrush_Holder_14995988": "pen_holder",
    "Cole_Hardware_Mug_Classic_Blue": "pen_holder",
    "Room_Essentials_Mug_White_Yellow": "pen_holder",
    # receptacles in general (L8-D ov_into__ request): bowls, a waste basket
    "Threshold_Porcelain_Serving_Bowl_Coupe_White": "bowl",
    "Threshold_Bead_Cereal_Bowl_White": "bowl",
    "Room_Essentials_Bowl_Turquiose": "bowl",
    "Cole_Hardware_Deep_Bowl_Good_Earth_1075": "bowl",
    "Bradshaw_International_11642_7_Qt_MP_Plastic_Bowl": "bowl",
    "Hefty_Waste_Basket_Decorative_Bronze_85_liter": "trash_can",
}
PH_CONTAINERS = {"wicker_basket_01": "basket", "wicker_basket_02": "basket", "wooden_bowl_01": "bowl",
                 "wooden_bowl_02": "bowl", "carved_wooden_plate": "plate", "wooden_cutting_board": "cutting_board",
                 "plastic_crate_01": "crate", "plastic_crate_02": "crate", "wooden_crate_01": "crate",
                 "cardboard_box_01": "box"}
THOR_CONTAINERS = ([("thor_Bowl", f"Bowl_{i}", "bowl") for i in range(1, 7)]
                   + [("thor_Plate", f"Plate_{i}", "plate") for i in range(1, 5)]
                   + [("thor_Pot_1", "Pot_1", "pot"), ("thor_Mug", "Mug_1", "cup"), ("thor_Mug", "Mug_2", "cup"),
                      ("thor_Cup", "Cup_1", "cup"), ("thor_Cup", "Cup_2", "cup")]
                   + [("thor_Sink", f"Sink_{i}", "sink") for i in range(1, 4)]
                   + [("thor_bin", f"bin_{i}", "trash_can") for i in (1, 10, 12, 13)])
PH_FRUIT = ("bananas", "food_apple_01", "food_pears_asian_01", "lemon")
BLENDERS = {  # id -> (jar height, inner radius bottom, inner radius top, base height, base radius)
    "blender_jar_a": (0.18, 0.045, 0.065, 0.10, 0.085),
    "blender_jar_b": (0.16, 0.050, 0.060, 0.08, 0.080),
}
WALL = 0.004
PEN_W = (0.005, 0.020)
GSO_LICENSE = "CC BY 4.0"
OURS = "ours (procedural geometry, tools/l8x_assets/import_task_assets.py)"


def inside_of(V, F, min_side: float = 0.03):
    """-> the container surface (largest container free box) in the canonical frame (bottom centre at the origin)
    with the opening box at the rim height, or None."""
    lo, hi = V.min(0), V.max(0)
    V0 = V - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    H = float(V0[:, 2].max())
    # floor: the largest support surface in the lower 60 % of the height (sloped / woven walls defeat the strict
    # rim-ring container test of mesh_support_surfaces, so the rim is measured separately)
    S = [s for s in SU.mesh_support_surfaces(V0, F, min_area=min_side * min_side, min_side=min_side)
         if s["top_z"] < 0.6 * H and s.get("covered_above") is None]
    if not S:
        return _onto(V0, F, min_side), V0
    s = max(S, key=lambda q: q["area"])
    (x0, x1), (y0, y1) = s["free_box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # rim: per 15-deg sector the highest outer-wall point; the median over sectors ignores a handle arc
    dx, dy = V0[:, 0] - cx, V0[:, 1] - cy
    ang, rad = np.arctan2(dy, dx), np.hypot(dx, dy)
    tops = []
    for k in range(24):
        m = (ang >= -math.pi + k * math.pi / 12) & (ang < -math.pi + (k + 1) * math.pi / 12)
        if m.any():
            r = rad[m]
            tops.append(float(V0[m][r >= 0.6 * r.max(), 2].max()))
    rim = float(np.median(tops))
    if rim - s["top_z"] < 0.03:
        return _onto(V0, F, min_side), V0
    # opening: along +-x / +-y from the floor centre, the nearest wall point in the band just below the rim
    band = V0[(V0[:, 2] > rim - 0.02) & (V0[:, 2] <= rim + 0.005)]

    def gap(axis, sign, fallback):
        other = 1 - axis
        c = (cx, cy)
        near = band[np.abs(band[:, other] - c[other]) < 0.01]
        vals = (near[:, axis] - c[axis]) * sign
        vals = vals[vals > 0]
        return float(vals.min()) if len(vals) else float(fallback)
    op = [[cx - gap(0, -1, cx - x0), cx + gap(0, 1, x1 - cx)], [cy - gap(1, -1, cy - y0), cy + gap(1, 1, y1 - cy)]]
    r4 = lambda v: round(float(v), 4)  # noqa: E731
    return {"place_kind": "into", "inner_floor_z": r4(s["top_z"]), "rim_z": r4(rim),
            "inner_box": [[r4(v) for v in s["free_box"][0]], [r4(v) for v in s["free_box"][1]]],
            "opening_box": [[r4(v) for v in op[0]], [r4(v) for v in op[1]]],
            "opening_min_side": r4(min(op[0][1] - op[0][0], op[1][1] - op[1][0])),
            "depth": r4(rim - s["top_z"])}, V0


def _onto(V0, F, min_side):
    """Flat place target (plate, cutting board, tray, lid-less low dish): the largest uncovered support surface
    above 30 % of the height -> place_kind "onto" (inner_box = its free box, rim_z None)."""
    H = float(V0[:, 2].max())
    S = [s for s in SU.mesh_support_surfaces(V0, F, min_area=min_side * min_side, min_side=min_side)
         if s.get("covered_above") is None and s["top_z"] >= 0.3 * H - 1e-6]
    if not S:
        return None
    s = max(S, key=lambda q: q["area"])
    r4 = lambda v: round(float(v), 4)  # noqa: E731
    box = [[r4(v) for v in s["free_box"][0]], [r4(v) for v in s["free_box"][1]]]
    return {"place_kind": "onto", "inner_floor_z": r4(s["top_z"]), "rim_z": None, "inner_box": box,
            "opening_box": box, "opening_min_side": r4(min(box[0][1] - box[0][0], box[1][1] - box[1][0])),
            "depth": 0.0}


def wrap_kinematic(src: str, dst: str) -> str:
    """A wrapper layer referencing a shared (THOR) USD: kinematic rigid body on the default prim (or on the prims
    that already have one) and triangle-mesh colliders, authored as overs so the shared asset is untouched."""
    from pxr import Usd, UsdGeom, UsdPhysics
    if os.path.exists(dst):
        os.remove(dst)
    st = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageUpAxis(st, UsdGeom.GetStageUpAxis(Usd.Stage.Open(src)))
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = st.DefinePrim("/Obj", "Xform")
    root.GetReferences().AddReference(src)
    st.SetDefaultPrim(root)
    bodies = [p for p in st.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    if not bodies:
        UsdPhysics.RigidBodyAPI.Apply(root)
    for p in st.Traverse():
        if p.HasAPI(UsdPhysics.RigidBodyAPI):
            UsdPhysics.RigidBodyAPI(p).CreateKinematicEnabledAttr(True)
        if p.IsA(UsdGeom.Mesh) and (p.HasAPI(UsdPhysics.CollisionAPI) or p.HasAPI(UsdPhysics.MeshCollisionAPI)):
            UsdPhysics.MeshCollisionAPI.Apply(p).CreateApproximationAttr("none")
    st.GetRootLayer().Save()
    return dst


def kinematic_triangle(usd: str) -> None:
    """Make a written rigid-body USD a kinematic body whose mesh colliders are triangle meshes."""
    from pxr import Usd, UsdPhysics
    st = Usd.Stage.Open(usd)
    for p in st.Traverse():
        if p.HasAPI(UsdPhysics.RigidBodyAPI):
            UsdPhysics.RigidBodyAPI(p).CreateKinematicEnabledAttr(True)
        if p.HasAPI(UsdPhysics.MeshCollisionAPI):
            UsdPhysics.MeshCollisionAPI(p).CreateApproximationAttr("none")
    st.GetRootLayer().Save()


def jar_mesh(h, r0, r1, bh, br, n=32):
    """Blender: a cylindrical motor base (bh tall, radius br) + an open tapered jar on it (walls WALL thick, inner
    radius r0 at the floor to r1 at the rim, floor WALL thick). -> V, F (z-up metres, bottom at z 0)."""
    V, F = [], []

    def ring(z, r):
        k = len(V)
        V.extend([(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), z) for i in range(n)])
        return k

    def band(a, b, out=True):
        for i in range(n):
            j = (i + 1) % n
            F.extend([(a + i, a + j, b + j), (a + i, b + j, b + i)] if out else
                     [(a + i, b + j, a + j), (a + i, b + i, b + j)])

    def cap(a, z, up):
        c = len(V)
        V.append((0.0, 0.0, z))
        for i in range(n):
            j = (i + 1) % n
            F.append((c, a + i, a + j) if up else (c, a + j, a + i))
    b0, b1 = ring(0.0, br), ring(bh, br)
    band(b0, b1)
    cap(b0, 0.0, False)
    cap(b1, bh, True)
    z0 = bh + 0.002
    o0, o1 = ring(z0, r0 + WALL), ring(z0 + h, r1 + WALL)
    i0, i1 = ring(z0 + WALL, r0), ring(z0 + h, r1)
    band(o0, o1)
    band(i0, i1, out=False)
    band(o1, i1, out=True)  # rim lip
    cap(o0, z0, False)
    cap(i0, z0 + WALL, True)
    return np.asarray(V, float), np.asarray(F, int)


def write_jar_usd(dst, V, F, colour=(0.82, 0.86, 0.9)):
    from pxr import Gf, Usd, UsdGeom, UsdPhysics, Vt
    if os.path.exists(dst):
        os.remove(dst)
    st = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, "/Obj")
    st.SetDefaultPrim(root.GetPrim())
    UsdPhysics.RigidBodyAPI.Apply(root.GetPrim()).CreateKinematicEnabledAttr(True)
    UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(1.5)
    m = UsdGeom.Mesh.Define(st, "/Obj/mesh")
    m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in V]))
    m.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(F)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray([int(i) for i in F.ravel()]))
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    m.CreateDisplayColorAttr(Vt.Vec3fArray([Gf.Vec3f(*colour)]))
    UsdPhysics.CollisionAPI.Apply(m.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(m.GetPrim()).CreateApproximationAttr("none")
    st.GetRootLayer().Save()


def container_row(cid, role, src, name, V, F, usd, license_, attribution, quat=(1.0, 0.0, 0.0, 0.0), ins=None):
    """objv-compatible row (objects_real fields; spawn_quat_wxyz is the pure up-axis quaternion, no caliper yaw, so
    the boxes stay in the root frame) + the place target: place_kind "into" / "onto", inner_floor_z, inner_box
    [[x0, x1], [y0, y1]] and rim_z (into only) RELATIVE TO THE ROOT (spawned with spawn_quat_wxyz, yaw 0); the
    canonical-frame (bottom centre at the origin) numbers stay under "inside" for the gate."""
    ins0, V0 = inside_of(V, F, 0.02 if role == "pen_holder" else 0.04)
    ins = ins or ins0
    lo, hi = V0.min(0), V0.max(0)
    ofr = (V.min(0) + V.max(0)) / 2
    rab = float(-V.min(0)[2])
    d = OR.descriptors(OR.sample_surface(V, F))
    r = RT.row(src, name, d, None, role, usd, list(quat), {"mass": 0.5, "attribution": attribution}, V=V, F=F)
    r4 = lambda v: round(float(v), 4)  # noqa: E731
    r.update({"id": cid, "role": role, "category": role, "license": license_, "kinematic": True,
              "spawn_quat_wxyz": list(quat), "centre_from_root_xy": [r4(ofr[0]), r4(ofr[1])],
              "half_extents": [r4(v / 2) for v in hi - lo], "size": [r4(v) for v in hi - lo],
              "height": r4(hi[2] - lo[2]), "footprint_r": r4(0.5 * np.hypot(hi[0] - lo[0], hi[1] - lo[1])),
              "origin_from_root": [r4(v) for v in ofr], "root_above_bottom": r4(rab), "inside": ins,
              "place_kind": None, "inner_floor_z": None, "inner_box": None, "rim_z": None})
    if ins:
        r.update({"place_kind": ins["place_kind"], "inner_floor_z": r4(ins["inner_floor_z"] - rab),
                  "inner_box": [[r4(ins["inner_box"][0][0] + ofr[0]), r4(ins["inner_box"][0][1] + ofr[0])],
                                [r4(ins["inner_box"][1][0] + ofr[1]), r4(ins["inner_box"][1][1] + ofr[1])]],
                  "rim_z": None if ins["rim_z"] is None else r4(ins["rim_z"] - rab),
                  "opening_box": [[r4(ins["opening_box"][0][0] + ofr[0]), r4(ins["opening_box"][0][1] + ofr[0])],
                                  [r4(ins["opening_box"][1][0] + ofr[1]), r4(ins["opening_box"][1][1] + ofr[1])]]})
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gso", required=True)
    ap.add_argument("--ph", required=True)
    ap.add_argument("--thor", required=True)
    ap.add_argument("--out-containers", required=True)
    ap.add_argument("--out-items", required=True)
    a = ap.parse_args(argv)
    cont, items, drop = {}, {}, {}
    from pxr import Usd
    for name, role in GSO_CONTAINERS.items():
        d0 = os.path.join(a.gso, name)
        try:
            V, T, F, FT = RT.read_obj(os.path.join(d0, "meshes", "model.obj"))
            usd = os.path.join(d0, "model_qdd_kin.usda")
            RT.write_gso_usd(usd, V, T, F, FT, "materials/textures/texture.png", 0.5)
            kinematic_triangle(usd)
            cid = IP.safe_id("cont_gso_" + name[:36])
            cont[cid] = container_row(cid, role, "Google Scanned Objects", name, V, F, usd, GSO_LICENSE,
                                      "Google LLC, Google Scanned Objects (CC BY 4.0)")
        except Exception as e:  # noqa: BLE001
            drop["gso:" + name] = f"{type(e).__name__}: {e}"[:120]
    for aid in list(PH_CONTAINERS) + list(PH_FRUIT):
        try:
            d0 = os.path.join(a.ph, aid)
            if not os.path.isdir(d0) or not any(f.endswith(".usdc") for f in os.listdir(d0)):
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from polyhaven_fetch import API, fetch, get
                f = json.loads(get(f"{API}/files/{aid}"))["usd"]["1k"]["usd"]
                fetch(f["url"], f["md5"], os.path.join(d0, os.path.basename(f["url"])))
                for rel, g in (f.get("include") or {}).items():
                    fetch(g["url"], g["md5"], os.path.join(d0, rel))
            src = os.path.join(d0, next(f for f in os.listdir(d0) if f.endswith(".usdc")))
            P, Fm = UI.render_mesh(Usd.Stage.Open(src))
            if aid in PH_CONTAINERS:
                col = os.path.join(d0, aid + "_col_tri.usda")
                IP._flat_with_colliders(src, col, "none")
                usd = os.path.join(d0, aid + "_kin.usda")
                IP._ph_product_usd(usd, col, 0.8)
                kinematic_triangle(usd)
                cid = "cont_ph_" + aid
                cont[cid] = container_row(cid, PH_CONTAINERS[aid], "Poly Haven", aid, P, Fm, usd, IP.PH_LICENSE,
                                          "Poly Haven (CC0)")
            else:
                d = OR.descriptors(OR.sample_surface(P, Fm))
                col = os.path.join(d0, aid + "_col.usda")
                IP._flat_with_colliders(src, col, "convexHull")
                usd = os.path.join(d0, aid + "_qdd.usda")
                IP._ph_product_usd(usd, col, IP.mass_of(d))
                r = RT.row("Poly Haven", aid, d, None, "fruit", usd, [1.0, 0.0, 0.0, 0.0],
                           {"mass": round(IP.mass_of(d), 3), "attribution": "Poly Haven (CC0)"}, V=P, F=Fm,
                           body_rel="geo")
                r.update(license=IP.PH_LICENSE, role="fruit")
                items["item_ph_" + aid] = r
        except Exception as e:  # noqa: BLE001
            drop["ph:" + aid] = f"{type(e).__name__}: {e}"[:120]
    for bid, (h, r0, r1, bh, br) in BLENDERS.items():
        V, F = jar_mesh(h, r0, r1, bh, br)
        d0 = os.path.join(os.path.dirname(a.out_containers), "blender_jars")
        os.makedirs(d0, exist_ok=True)
        usd = os.path.join(d0, bid + ".usda")
        write_jar_usd(usd, V, F)
        exact = {"place_kind": "into", "inner_floor_z": round(bh + 0.002 + WALL, 4),  # exact geometry
                 "rim_z": round(bh + 0.002 + h, 4), "opening_radius": r1, "floor_radius": r0,
                 "inner_box": [[-r0 / 1.415, r0 / 1.415], [-r0 / 1.415, r0 / 1.415]],
                 "opening_box": [[-r1, r1], [-r1, r1]], "opening_min_side": round(2 * r1, 4), "depth": h - WALL}
        cont["cont_" + bid] = container_row("cont_" + bid, "blender", "procedural", bid, V, F, usd, OURS, "ours",
                                            ins=exact)
    for pkg, var, role in THOR_CONTAINERS:
        src = os.path.join(a.thor, pkg, var, var + ".usda")
        try:
            P, Fm = UI.render_mesh(Usd.Stage.Open(src))
            V = np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)
            d0 = os.path.join(os.path.dirname(a.out_containers), "task_containers")
            os.makedirs(d0, exist_ok=True)
            usd = wrap_kinematic(src, os.path.join(d0, var + "_kin.usda"))
            cid = "cont_thor_" + var
            cont[cid] = container_row(cid, role, "MolmoSpaces THOR (AI2-THOR assets)", var, V, Fm, usd,
                                      GSO_LICENSE, "AI2-THOR / MolmoSpaces (CC BY 4.0)",
                                      quat=(0.7071068, 0.7071068, 0.0, 0.0))
        except Exception as e:  # noqa: BLE001
            drop["thor:" + var] = f"{type(e).__name__}: {e}"[:120]
    for pkg in ("thor_Pen", "thor_Pencil"):
        for var in sorted(os.listdir(os.path.join(a.thor, pkg))):
            if var.endswith(("_mesh", "_prim")):
                continue
            usd = os.path.join(a.thor, pkg, var, var + ".usda")
            try:
                P, Fm = UI.render_mesh(Usd.Stage.Open(usd))
                V = np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)
                d = OR.descriptors(OR.sample_surface(V, Fm))
                if not PEN_W[0] <= d["grasp_width"] <= PEN_W[1]:
                    drop["thor:" + var] = f"grasp {d['grasp_width']:.3f}"
                    continue
                r = RT.row("MolmoSpaces THOR (AI2-THOR assets)", var, d, None, "pen", usd,
                           [0.7071068, 0.7071068, 0.0, 0.0],
                           {"mass": 0.02, "attribution": "AI2-THOR / MolmoSpaces (CC BY 4.0)"}, V=V, F=Fm,
                           body_rel="Geometry/" + var)
                r.update(role="pen")
                items["item_thor_" + var] = r
            except Exception as e:  # noqa: BLE001
                drop["thor:" + var] = f"{type(e).__name__}: {e}"[:120]
    for k, o in items.items():
        o["size_word"] = None
        o["task_name"] = OR.task_name(o, None)
        o["name"], o["uid"], o["split"] = o["task_name"], k, IP.split_of(k)
    json.dump({"license": "CC BY 4.0 (GSO, THOR) / CC0 1.0 (Poly Haven) / ours (blender jars)", "containers": cont,
               "dropped": drop}, open(a.out_containers, "w"), indent=1)
    json.dump({"license": "CC0 1.0 (Poly Haven fruit) / CC BY 4.0 (THOR pens)", "objects": items, "dropped": drop},
              open(a.out_items, "w"), indent=1)
    from collections import Counter
    print("containers", len(cont), dict(Counter(c["role"] for c in cont.values())),
          "with inside", sum(bool(c["inside"]) for c in cont.values()), "items", len(items),
          dict(Counter(o["role"] for o in items.values())), "dropped", drop)


if __name__ == "__main__":
    main()
