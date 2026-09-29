"""Ring-on-peg assets V (coordinator: 'put the donut ring on the peg', ~3 % of L8S; procedural, licence ours; pylib pxr).

peg  : a round base (radius 5 cm, 1.5 cm high) with an upright post (radius PEG_R, height PEG_H) -- static colliders
       (cylinders), one colour per variant.
ring : a flat torus (centre radius Rc, tube radius t), inner diameter = peg diameter + GAP; a dynamic rigid body whose
       collider is N_SEG capsules around the circle (a torus needs a non-convex collider), the render mesh a torus;
       mass 40 g. One colour / material word per variant.
source block: a cuboid 7 cm high under the ring's -x part (the ring overhangs +x so the pads can pinch its tube
       at the +x side; a flat ring on the table is too low for the top-down fingers: tips 2.25 cm below the TCP).
Variants: GAPS (3.5 / 3.0 / 2.5 cm -- start wide, narrow after the gate) x colours; names "<colour> ring" / "<colour>
peg" must be unique within a scene (name check: ring and peg colours differ).
CPU check: inner diameter - peg diameter = gap, outer diameter <= 9 cm, tube <= 1.5 cm (the pads close on it),
the block edge clears the inner fingers (>= 1.5 cm inside the ring's inner edge at +x).
usage: python tools/l8x_assets/ring_assets.py OUT_DIR"""
from __future__ import annotations

import json
import math
import os
import sys

PEG_R, PEG_H, BASE_R, BASE_H = 0.010, 0.15, 0.05, 0.015
TUBE_R = 0.006
GAPS = (0.035, 0.030, 0.025)
N_SEG = 16
BLOCK_H = 0.07
COLOURS = {"red": (0.80, 0.12, 0.10), "blue": (0.10, 0.25, 0.80), "green": (0.10, 0.55, 0.20),
           "yellow": (0.90, 0.78, 0.10), "orange": (0.95, 0.45, 0.08), "purple": (0.45, 0.18, 0.60),
           "white": (0.90, 0.90, 0.88), "black": (0.08, 0.08, 0.08)}
PEG_COLOURS = {"wooden": (0.55, 0.40, 0.25), "grey": (0.55, 0.55, 0.56), "black": (0.08, 0.08, 0.08),
               "white": (0.90, 0.90, 0.88)}


def ring_dims(gap: float) -> dict:
    inner = 2 * PEG_R + gap
    rc = inner / 2 + TUBE_R
    return {"gap": gap, "inner_d": round(inner, 4), "centre_r": round(rc, 4), "tube_r": TUBE_R,
            "outer_d": round(2 * (rc + TUBE_R), 4), "height": 2 * TUBE_R}


def check(d: dict) -> list:
    why = []
    if abs(d["inner_d"] - 2 * PEG_R - d["gap"]) > 1e-6:
        why.append("gap")
    if d["outer_d"] > 0.09:
        why.append(f"outer {d['outer_d']:.3f} > 0.09")
    if 2 * d["tube_r"] > 0.015:
        why.append("tube too thick for the pads")
    if d["centre_r"] - d["tube_r"] - 0.015 < 0.005:  # block edge inside the inner edge, >= 0.5 cm of ring on it
        why.append("no room for the source block under the ring")
    return why


def _mat(st, path, rgb):
    from pxr import Gf, Sdf, UsdShade
    m = UsdShade.Material.Define(st, path)
    sh = UsdShade.Shader.Define(st, path + "/PBR")
    sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
    m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    return m


def torus_mesh(rc, t, nu=48, nv=16):
    P, F = [], []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        for j in range(nv):
            b = 2 * math.pi * j / nv
            r = rc + t * math.cos(b)
            P.append((r * math.cos(a), r * math.sin(a), t * math.sin(b)))
    for i in range(nu):
        for j in range(nv):
            a, b = i * nv + j, ((i + 1) % nu) * nv + j
            c, d = ((i + 1) % nu) * nv + (j + 1) % nv, i * nv + (j + 1) % nv
            F.append((a, b, c, d))
    return P, F


def write_ring(dst: str, d: dict, rgb, mass: float = 0.04) -> None:
    from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade, Vt
    if os.path.exists(dst):
        os.remove(dst)
    st = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, "/Ring")
    st.SetDefaultPrim(root.GetPrim())
    UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
    UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(mass)
    rc, t = d["centre_r"], d["tube_r"]
    P, F = torus_mesh(rc, t)
    m = UsdGeom.Mesh.Define(st, "/Ring/visual")
    m.CreatePointsAttr(Vt.Vec3fArray(P))
    m.CreateFaceVertexCountsAttr(Vt.IntArray([4] * len(F)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray([i for f in F for i in f]))
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.catmullClark)
    UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(_mat(st, "/Ring/Looks/mat", rgb))
    seg = 2 * rc * math.sin(math.pi / N_SEG)
    for k in range(N_SEG):  # capsules along the circle (collision only)
        a = 2 * math.pi * (k + 0.5) / N_SEG
        c = UsdGeom.Capsule.Define(st, f"/Ring/col_{k}")
        c.CreateRadiusAttr(t)
        c.CreateHeightAttr(seg)
        c.CreateAxisAttr("Y")  # along the tangent after the yaw below
        xf = UsdGeom.Xformable(c)
        xf.AddTranslateOp().Set(Gf.Vec3d(rc * math.cos(a), rc * math.sin(a), 0.0))
        xf.AddRotateZOp().Set(math.degrees(a))
        c.CreatePurposeAttr(UsdGeom.Tokens.guide)
        UsdPhysics.CollisionAPI.Apply(c.GetPrim())
    st.GetRootLayer().Save()


def write_peg(dst: str, rgb) -> None:
    from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade
    if os.path.exists(dst):
        os.remove(dst)
    st = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = UsdGeom.Xform.Define(st, "/Peg")
    st.SetDefaultPrim(root.GetPrim())
    mat = _mat(st, "/Peg/Looks/mat", rgb)
    for name, r, h, z in (("base", BASE_R, BASE_H, BASE_H / 2), ("post", PEG_R, PEG_H, BASE_H + PEG_H / 2)):
        c = UsdGeom.Cylinder.Define(st, f"/Peg/{name}")
        c.CreateRadiusAttr(r)
        c.CreateHeightAttr(h)
        c.CreateAxisAttr("Z")
        UsdGeom.Xformable(c).AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, z))
        UsdPhysics.CollisionAPI.Apply(c.GetPrim())
        UsdShade.MaterialBindingAPI.Apply(c.GetPrim()).Bind(mat)
    st.GetRootLayer().Save()


def main(argv=None):
    out = (argv or sys.argv[1:])[0]
    os.makedirs(out, exist_ok=True)
    rows = {"rings": {}, "pegs": {}, "peg": {"radius": PEG_R, "height": PEG_H, "base_r": BASE_R, "base_h": BASE_H,
                                             "top_z": BASE_H + PEG_H}, "block_h": BLOCK_H, "license": "ours"}
    for gap in GAPS:
        d = ring_dims(gap)
        why = check(d)
        for cname, rgb in COLOURS.items():
            rid = f"ring_g{int(round(gap * 1000))}_{cname}"
            usd = os.path.join(out, rid + ".usda")
            write_ring(usd, d, rgb)
            rows["rings"][rid] = dict(d, colour=cname, name=f"{cname} ring", usd=usd, ok=not why, why=why,
                                      mass=0.04)
    for cname, rgb in PEG_COLOURS.items():
        pid = f"peg_{cname}"
        usd = os.path.join(out, pid + ".usda")
        write_peg(usd, rgb)
        rows["pegs"][pid] = {"colour": cname, "name": f"{cname} peg", "usd": usd}
    json.dump(rows, open(os.path.join(out, "rings.json"), "w"), indent=1)
    print("rings", len(rows["rings"]), "ok", sum(r["ok"] for r in rows["rings"].values()), "pegs", len(rows["pegs"]),
          {g: ring_dims(g) for g in GAPS})


if __name__ == "__main__":
    main()
