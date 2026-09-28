"""Store products and display fixtures for b4 (user-log 175 / 176; pod, pylib python: pxr + numpy + Pillow).

products (harvest/sim/assets_x/products.json, objv-compatible rows like objects_real, ids "prod_*"):
  GSO (CC BY 4.0) boxes / bottles / cans / jars / packs at their REAL size: categories Consumer Goods, Bottles and
  Cans and Cups, Media Cases, Board Games, or an uncategorised model whose claimed noun is a product noun; height
  2-35 cm, footprint 1.5-30 cm; no shoes / toys / bags. Poly Haven (CC0) role "product" models (food, containers,
  dishes) with the same size box. Each gets a rigid-body USD (convex-hull colliders, mass from the box, 600 kg/m^3 x
  0.4 fill), the canonical fields of real_table.row (spawn quaternion, half extents, top surface -- where another
  object can stand on it) and name_check. Products are shelf / clutter items; a product is also a pick target only
  if it passes the object gate size (7-10 cm, grasp 2.5-8.5 cm) -- task_target_ok stays with objv_mark_stable.
fixtures (harvest/sim/assets_x/assets_ph.json, the mesh-table format of assets_cyclo.json, tag "ph"): Poly Haven
  (CC0) role "fixture" models (shelves, cabinets, display furniture): every mesh a static triangle-mesh collider,
  usd_import.make_static (declared) + inspect (support surfaces from the collider mesh); category shelf (open tiers)
  or counter (a closed top), yaw -90 deg like THOR (front towards the robot), split by id hash (20 % ood).
usage: python tools/l8x_assets/import_products.py --gso DIR --gso-meta models.json --ph DIR --out-products P.json
       --out-fixtures F.json"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import objects_real as OR  # noqa: E402
from harvest.sim.assets_x import usd_import as UI  # noqa: E402
from tools.l8x_assets import real_table as RT  # noqa: E402

GSO_CATS = ("Consumer Goods", "Bottles and Cans and Cups", "Media Cases", "Board Games")
PRODUCT_NOUNS = {"box", "bottle", "can", "jar", "container", "cosmetic", "case", "medicine box", "cereal", "pack",
                 "carton", "tin", "cup", "mug", "bowl", "tube", "game cartridge", "cartridge", "sponge", "spray"}
NOT_PRODUCT = {"shoe", "toy", "toy animal", "toy vehicle", "bag", "hat", "SKIP"}
H_RANGE, FOOT_RANGE = (0.02, 0.35), (0.015, 0.30)
PH_LICENSE = "CC0 1.0 (Poly Haven, https://polyhaven.com/license)"


def safe_id(s: str) -> str:
    """Prim-path safe id (USD names: ASCII letters, digits, underscore)."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def split_of(key: str) -> str:
    return "ood" if int(hashlib.sha256(f"l8x-product:{key}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < 0.2 \
        else "train"


def size_ok(d: dict) -> bool:
    return H_RANGE[0] <= d["height"] <= H_RANGE[1] and FOOT_RANGE[0] <= d["grasp_width"] and \
        d["length"] <= FOOT_RANGE[1]


def mass_of(d: dict) -> float:
    return float(np.clip(d["height"] * d["grasp_width"] * d["length"] * 0.4 * 600, 0.05, 3.0))


def gso_products(gso: str, meta: str) -> tuple:
    cats = {r["name"]: (r.get("categories") or [""])[0] for r in json.load(open(meta))}
    out, drop = {}, {}
    for name in sorted(os.listdir(gso)):
        d0 = os.path.join(gso, name)
        obj = os.path.join(d0, "meshes", "model.obj")
        if not os.path.exists(obj):
            continue
        cat, claim = cats.get(name, ""), OR.claimed_noun(name, cats.get(name, ""))
        if claim in NOT_PRODUCT or not (cat in GSO_CATS or claim in PRODUCT_NOUNS):
            continue
        try:
            V, T, F, FT = RT.read_obj(obj)
            d = OR.descriptors(OR.sample_surface(V, F))
            if not size_ok(d):
                drop["gso:" + name] = f"size h {d['height']:.3f} w {d['grasp_width']:.3f} l {d['length']:.3f}"
                continue
            usd = os.path.join(d0, "model_qdd.usda")
            m = mass_of(d)
            if not os.path.exists(usd):
                RT.write_gso_usd(usd, V, T, F, FT, "materials/textures/texture.png", m)
            tex = os.path.join(d0, "materials", "textures", "texture.png")
            colour = OR.colour_word(RT.texture_colour(tex, T)) if os.path.exists(tex) else None
            r = RT.row("Google Scanned Objects (Gazebo Fuel GoogleResearch)", name, d, colour, claim, usd,
                       [1.0, 0.0, 0.0, 0.0], {"mass": round(m, 3), "category_src": cat,
                                              "attribution": "Google LLC, Google Scanned Objects (CC BY 4.0)"},
                       V=V, F=F, body_rel="")
            out[safe_id("prod_gso_" + name[:36])] = r
        except Exception as e:  # noqa: BLE001
            drop["gso:" + name] = f"{type(e).__name__}: {e}"[:100]
    return out, drop


def _flat_with_colliders(src: str, dst: str, approx: str) -> None:
    """Flattened copy of src with every Mesh a collider (approx: "none" = triangle mesh / "convexHull")."""
    from pxr import Sdf, Usd
    layer = Usd.Stage.Open(src).Flatten()

    def visit(spec):
        if spec.typeName == "Mesh":
            info = spec.GetInfo("apiSchemas") if spec.HasInfo("apiSchemas") else Sdf.TokenListOp()
            items = list(info.GetAddedOrExplicitItems())
            for api in ("PhysicsCollisionAPI", "PhysicsMeshCollisionAPI"):
                if api not in items:
                    items.append(api)
            lo = Sdf.TokenListOp()
            lo.prependedItems = items
            spec.SetInfo("apiSchemas", lo)
            a = Sdf.AttributeSpec(spec, "physics:approximation", Sdf.ValueTypeNames.Token, Sdf.VariabilityUniform)
            a.default = approx
        for c in spec.nameChildren:
            visit(c)
    for root in layer.rootPrims:
        visit(root)
    layer.Export(dst)


def _ph_product_usd(dst: str, col_layer: str, mass: float) -> None:
    """Rigid-body wrapper: /Obj (RigidBody + Mass) referencing the collider copy (Z-up metres, checked)."""
    from pxr import Usd, UsdGeom, UsdPhysics
    if os.path.exists(dst):
        os.remove(dst)
    st = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(st, "/Obj")
    st.SetDefaultPrim(root.GetPrim())
    UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
    UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(float(mass))
    g = UsdGeom.Xform.Define(st, "/Obj/geo")
    g.GetPrim().GetReferences().AddReference(os.path.basename(col_layer))
    st.GetRootLayer().Save()


def ph_models(ph: str) -> tuple:
    from pxr import Usd, UsdGeom
    models = json.load(open(os.path.join(ph, "models.json")))["models"]
    prods, fixt, drop = {}, {}, {}
    for aid, m in sorted(models.items()):
        if not m.get("usd"):
            drop["ph:" + aid] = "no usd"
            continue
        src = os.path.join(ph, m["usd"])
        try:
            st = Usd.Stage.Open(src)
            if str(UsdGeom.GetStageUpAxis(st)) != "Z" or abs(UsdGeom.GetStageMetersPerUnit(st) - 1.0) > 1e-6:
                drop["ph:" + aid] = "not Z-up metres"
                continue
            d0 = os.path.dirname(src)
            if m["role"] == "product":
                P, F = UI.render_mesh(st)
                d = OR.descriptors(OR.sample_surface(P, F))
                if not size_ok(d):
                    drop["ph:" + aid] = f"size h {d['height']:.3f} w {d['grasp_width']:.3f} l {d['length']:.3f}"
                    continue
                col = os.path.join(d0, aid + "_col.usda")
                _flat_with_colliders(src, col, "convexHull")
                usd = os.path.join(d0, aid + "_qdd.usda")
                _ph_product_usd(usd, col, mass_of(d))
                claim = OR.claimed_noun(m["name"] or aid)
                r = RT.row("Poly Haven", aid, d, None, claim, usd, [1.0, 0.0, 0.0, 0.0],
                           {"mass": round(mass_of(d), 3), "category_src": ",".join(m.get("categories") or []),
                            "attribution": "Poly Haven: " + ", ".join(m.get("authors") or []) + " (CC0)"},
                           V=P, F=F, body_rel="geo")
                r["license"] = PH_LICENSE
                prods[safe_id("prod_ph_" + aid[:40])] = r
            else:
                col = os.path.join(d0, aid + "_col.usda")
                _flat_with_colliders(src, col, "none")
                s = UI.make_static(col, mode="declared")
                ins = UI.inspect(s["dst"], exact_mesh=True)
                surfs = [x for x in ins["surfaces"] if x["top_z"] > 0.05]
                if not surfs:
                    drop["ph:" + aid] = "no support surface"
                    continue
                tiers = sum(1 for x in surfs if x.get("covered_above") is not None)
                fixt[aid] = {"tag": "ph", "category": "shelf" if tiers else "counter",
                             "top_kind": "shelf" if tiers else "table", "yaw": -math.pi / 2, "dst": s["dst"],
                             "src": src, "collider_size": ins["collider_size"], "render_size": ins["render_size"],
                             "origin_offset": ins["origin_offset"],
                             "render_vs_collider_mm": ins["render_vs_collider_mm"], "n_colliders": ins["n_colliders"],
                             "surfaces": surfs, "split": split_of(aid), "license": PH_LICENSE,
                             "source": m["source"], "authors": m.get("authors")}
        except Exception as e:  # noqa: BLE001
            drop["ph:" + aid] = f"{type(e).__name__}: {e}"[:120]
    return prods, fixt, drop


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gso")
    ap.add_argument("--gso-meta")
    ap.add_argument("--ph")
    ap.add_argument("--out-products", required=True)
    ap.add_argument("--out-fixtures", required=True)
    a = ap.parse_args(argv)
    prods, drop, fixt = {}, {}, {}
    if a.gso:
        p, dr = gso_products(a.gso, a.gso_meta)
        prods.update(p)
        drop.update(dr)
    if a.ph:
        p, f, dr = ph_models(a.ph)
        prods.update(p)
        fixt.update(f)
        drop.update(dr)
    sw = OR.size_words(prods)
    for k, o in prods.items():
        o["size_word"] = sw.get(k)
        o["task_name"] = OR.task_name(o, sw.get(k))
        o["name"], o["uid"], o["split"] = o["task_name"], k, split_of(k)
        o["role"] = "product"
    json.dump({"license": "CC BY 4.0 (GSO) / CC0 1.0 (Poly Haven)", "objects": prods, "dropped": drop},
              open(a.out_products, "w"), indent=1)
    json.dump({"license": PH_LICENSE, "source": "Poly Haven models (api.polyhaven.com)", "assets": fixt,
               "dropped": {k: v for k, v in drop.items() if k.startswith("ph:")}}, open(a.out_fixtures, "w"), indent=1)
    from collections import Counter
    print("products", len(prods), dict(Counter(k.split("_")[1] for k in prods)), "fixtures", len(fixt),
          dict(Counter(f["category"] for f in fixt.values())), "dropped", len(drop))
    print("nouns", Counter(o["noun"] for o in prods.values()).most_common(25))


if __name__ == "__main__":
    main()
