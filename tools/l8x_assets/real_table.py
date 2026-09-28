"""Real everyday objects for L8-X (pod; pxr + numpy + Pillow from /data/harvest/assets_x/pylib).

Sources (all CC BY 4.0): Google Scanned Objects (GSO, Gazebo Fuel GoogleResearch: meshes/model.obj +
materials/textures/texture.png, metres, z up, scanned in the resting pose) and MolmoSpaces THOR props (USD, Y-up).
Per object: resting-pose vertices -> objects_real.descriptors; colour = median texture colour at the mesh's UVs (GSO);
claimed noun from the source name -> name_check (shape must support it); size gate (height <= 10.5 cm, grasp width
1.6-9 cm, length <= 30 cm); pose "upright" or "lying" (height < 0.8 x grasp width: shoes, flat packs).
GSO objects get a USD written next to their OBJ (model_qdd.usda: rigid body + mass, the scan mesh with a convex-hull
collider, UsdPreviewSurface with the scan texture). Split: noun hash, 20 % of nouns -> ood_o.
usage: python tools/l8x_assets/real_table.py --gso DIR --thor DIR --out real_objects.json"""
from __future__ import annotations

import argparse
import math
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import objects_real as OR  # noqa: E402

H_MAX, W_RANGE, L_MAX = 0.105, (0.016, 0.090), 0.30
THOR_PROPS = ("Mug", "Cup", "Bowl", "Apple", "Tomato", "Potato", "Egg", "Bread", "Salt_Shaker", "Pepper_Shaker",
              "Soap_B", "Spray_Bottle", "Tissue_Box", "Remote", "Cellphone", "Candle", "Bottle", "Wine_Bottle",
              "Box", "Book", "Dish_Sponge", "Alarm_Clock", "Watch", "Keychain", "CreditCard", "Pen", "Pencil",
              "Plate", "Lettuce", "Kettle", "Toaster", "Pot", "Pan")
LICENSE = "CC BY 4.0"


def split_of(noun: str) -> str:
    h = int(hashlib.sha256(("l8x-real-ood:" + noun).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "ood_o" if h < 0.2 else "train"


def read_obj(path):
    V, T, F, FT = [], [], [], []
    with open(path) as f:
        for ln in f:
            if ln.startswith("v "):
                V.append([float(x) for x in ln.split()[1:4]])
            elif ln.startswith("vt "):
                T.append([float(x) for x in ln.split()[1:3]])
            elif ln.startswith("f "):
                ids = [p.split("/") for p in ln.split()[1:]]
                vi = [int(p[0]) - 1 for p in ids]
                ti = [int(p[1]) - 1 if len(p) > 1 and p[1] else -1 for p in ids]
                for k in range(1, len(vi) - 1):  # fan
                    F.append([vi[0], vi[k], vi[k + 1]])
                    FT.append([ti[0], ti[k], ti[k + 1]])
    return np.asarray(V, float), np.asarray(T, float), np.asarray(F, int), np.asarray(FT, int)


def texture_colour(png, T):
    from PIL import Image
    im = np.asarray(Image.open(png).convert("RGB"))
    H, W = im.shape[:2]
    if len(T) == 0:
        return None
    u = np.clip((T[:, 0] % 1.0) * (W - 1), 0, W - 1).astype(int)
    v = np.clip((1 - T[:, 1] % 1.0) * (H - 1), 0, H - 1).astype(int)
    return [int(c) for c in np.median(im[v, u], axis=0)]


def write_gso_usd(dst, V, T, F, FT, tex_rel, mass):
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, Vt
    st = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, "/Obj")
    st.SetDefaultPrim(root.GetPrim())
    UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
    UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(float(mass))
    m = UsdGeom.Mesh.Define(st, "/Obj/mesh")
    m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in V]))
    m.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(F)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray([int(i) for i in F.ravel()]))
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    if len(T) and (FT >= 0).all():
        pv = UsdGeom.PrimvarsAPI(m).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                                  UsdGeom.Tokens.faceVarying)
        pv.Set(Vt.Vec2fArray([Gf.Vec2f(*t) for t in T]))
        pv.SetIndices(Vt.IntArray([int(i) for i in FT.ravel()]))
    UsdPhysics.CollisionAPI.Apply(m.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(m.GetPrim()).CreateApproximationAttr("convexHull")
    mat = UsdShade.Material.Define(st, "/Obj/Looks/mat")
    sh = UsdShade.Shader.Define(st, "/Obj/Looks/mat/pbr")
    sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.6)
    rd = UsdShade.Shader.Define(st, "/Obj/Looks/mat/st")
    rd.CreateIdAttr("UsdPrimvarReader_float2")
    rd.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    tx = UsdShade.Shader.Define(st, "/Obj/Looks/mat/tex")
    tx.CreateIdAttr("UsdUVTexture")
    tx.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(tex_rel)
    tx.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(rd.ConnectableAPI(), "result")
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tx.ConnectableAPI(), "rgb")
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat)
    st.GetRootLayer().Save()


def gate(d):
    why = []
    if d["height"] > H_MAX:
        why.append(f"height {d['height']:.3f}")
    if not W_RANGE[0] <= d["grasp_width"] <= W_RANGE[1]:
        why.append(f"grasp {d['grasp_width']:.3f}")
    if d["length"] > L_MAX:
        why.append(f"length {d['length']:.3f}")
    return why


def row(src, name, d, colour, claim, usd, quat, extra, V=None, F=None, body_rel=""):
    """Table row; also the objv-compatible canonical fields (prereg_l8x_tasks 1): the caliper yaw folded into the
    spawn quaternion (narrow side along canonical x), the caliper box centre as centre_from_root_xy, half extents
    (width, length, height) / 2, body_rel, and the top support surface (stacking base) in the canonical frame."""
    nc = OR.name_check(claim, d)
    a = d["grasp_yaw"]
    qz = (math.cos(-a / 2), 0.0, 0.0, math.sin(-a / 2))
    canon = {"spawn_quat_wxyz": [round(float(v), 7) for v in _qmul(qz, quat)],
             "centre_from_root_xy": d["caliper_centre"],
             "half_extents": [round(d["grasp_width"] / 2, 4), round(d["length"] / 2, 4), round(d["height"] / 2, 4)],
             "body_rel": body_rel,
             "top_surface": OR.top_surface(OR.canonical(V, d), F, d) if V is not None and F is not None else None}
    return dict(d, source=src, source_name=name, colour=colour, noun=nc["noun"], name_check=nc, usd_physics=usd,
                root_above_bottom=round(-d["bottom_z"], 4), category=nc["noun"],
                pose="upright" if d["height"] >= 0.8 * d["grasp_width"] else "lying", license=LICENSE, **canon,
                **extra)


def _qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gso", default=None)
    ap.add_argument("--gso-meta", default=None, help="gso_fetch list output (categories)")
    ap.add_argument("--thor", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out, drop = {}, {}
    cats = {r["name"]: (r.get("categories") or [""])[0] for r in json.load(open(a.gso_meta))} if a.gso_meta else {}
    if a.gso:
        for name in sorted(os.listdir(a.gso)):
            d0 = os.path.join(a.gso, name)
            obj = os.path.join(d0, "meshes", "model.obj")
            if not os.path.exists(obj):
                continue
            try:
                V, T, F, FT = read_obj(obj)
                d = OR.descriptors(OR.sample_surface(V, F))
                why = gate(d) + (["sharp object"] if OR.claimed_noun(name, cats.get(name, "")) == "SKIP" else [])
                if why:
                    drop["gso:" + name] = "; ".join(why)
                    continue
                tex = os.path.join(d0, "materials", "textures", "texture.png")
                colour = OR.colour_word(texture_colour(tex, T)) if os.path.exists(tex) else None
                mass = float(np.clip(d["height"] * d["grasp_width"] * d["length"] * 0.4 * 600, 0.05, 1.0))
                usd = os.path.join(d0, "model_qdd.usda")
                write_gso_usd(usd, V, T, F, FT, "materials/textures/texture.png", mass)
                out["gso_" + name[:40]] = row("Google Scanned Objects (Gazebo Fuel GoogleResearch)", name, d, colour,
                                              OR.claimed_noun(name, cats.get(name, "")), usd, [1.0, 0.0, 0.0, 0.0],
                                              {"mass": round(mass, 3), "category_src": cats.get(name, ""),
                                               "attribution": "Google LLC, Google Scanned Objects (CC BY 4.0)"},
                                              V=V, F=F, body_rel="")
            except Exception as e:  # noqa: BLE001
                drop["gso:" + name] = f"{type(e).__name__}: {e}"[:100]
    if a.thor:
        from pxr import Usd

        from harvest.sim.assets_x.usd_import import render_mesh
        for pkg in sorted(os.listdir(a.thor)):
            base = pkg.replace("thor_", "")
            if not any(base == p or base.startswith(p + "_") for p in THOR_PROPS):
                continue
            for var in sorted(os.listdir(os.path.join(a.thor, pkg))):
                if var.endswith(("_mesh", "_prim")) or " " in var:
                    continue
                usd = os.path.join(a.thor, pkg, var, var + ".usda")
                if not os.path.exists(usd):
                    continue
                try:
                    P, Fm = render_mesh(Usd.Stage.Open(usd))
                    V = np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)  # rotateX +90: Y-up -> z-up
                    d = OR.descriptors(OR.sample_surface(V, Fm))
                    why = gate(d) + (["sharp object"] if OR.claimed_noun(var) == "SKIP" else [])
                    if why:
                        drop["thor:" + var] = "; ".join(why)
                        continue
                    out["thor_" + var] = row("MolmoSpaces THOR (AI2-THOR assets)", var, d, None,
                                             OR.claimed_noun(var), usd, [0.7071068, 0.7071068, 0.0, 0.0],
                                             {"mass": round(float(np.clip(d["height"] * d["grasp_width"] * d["length"]
                                                                          * 0.4 * 600, 0.05, 1.0)), 3), "category_src": pkg,
                                              "attribution": "AI2-THOR / MolmoSpaces (CC BY 4.0)"},
                                             V=V, F=Fm, body_rel="Geometry/" + var)
                except Exception as e:  # noqa: BLE001
                    drop["thor:" + var] = f"{type(e).__name__}: {e}"[:100]
    sw = OR.size_words(out)
    for k, o in out.items():
        o["size_word"] = sw.get(k)
        o["task_name"] = OR.task_name(o, sw.get(k))
        o["name"], o["uid"] = o["task_name"], k  # objv.register fields
        o["split"] = split_of(o["noun"])
    res = {"license": LICENSE, "gates": {"height_max": H_MAX, "grasp_width": W_RANGE, "length_max": L_MAX},
           "objects": out, "dropped": drop}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    nouns = {}
    for o in out.values():
        nouns[o["noun"]] = nouns.get(o["noun"], 0) + 1
    print("objects", len(out), "dropped", len(drop), "renamed", sum(o["name_check"]["renamed"] for o in out.values()))
    print("nouns", sorted(nouns.items(), key=lambda kv: -kv[1]))
    print("split", {s: sum(o["split"] == s for o in out.values()) for s in ("train", "ood_o")})


if __name__ == "__main__":
    main()
