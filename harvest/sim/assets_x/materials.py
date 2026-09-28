"""CC0 PBR material + HDR environment library for the realistic bundle b4 (user-log 173; helper L8X-assets).

Catalog: /data/harvest/assets_x/materials/materials.json (tools/l8x_assets/polyhaven_fetch.py; Poly Haven, every
asset CC0 1.0): textures (1k JPG diffuse / normal GL / roughness) with a role -- furniture (wood), floor, wall, fabric
-- and indoor HDRIs (2k .hdr, role env). usable(): complete downloads, minus the API's loose "indoor" floors / walls
that look outdoor or derelict (DENY categories / tags). split_of(): 20 % of each role held out by id hash ("ood", for
an appearance OOD set), the rest "train". pick(): a seeded choice per role.
USD side (pod, pxr): author() makes a UsdPreviewSurface material (diffuse / normal / roughness textures, UV scale =
tiles per metre x the part size), bind() binds it to a prim (stronger than descendants), set_dome() points the dome
light at an HDRI. Nothing here is used by the existing runner paths; L8-D opts in for b4."""
from __future__ import annotations

import hashlib
import json
import os

ROOT = "/data/harvest/assets_x/materials"
DENY = {"dirty", "terrain", "rock", "aerial", "road", "asphalt", "sand", "snow", "gravel", "bark", "roofing",
        "cobblestone", "natural"}
DENY_TAGS = {"rubble", "debris", "demolition", "abandoned", "crumbling", "broken", "moss", "grass", "dirt", "mud",
             "rusty", "rust"}
OOD_SHARE = 0.2
ENV_DENY = ("abandoned", "derelict", "ruin", "underpass", "garage", "tunnel", "construction")
ROLES = ("furniture", "floor", "wall", "fabric", "env")


def load(root: str = ROOT) -> dict:
    return json.load(open(os.path.join(root, "materials.json")))["materials"]


def usable(cat: dict, tags: dict | None = None) -> dict:
    """Complete, not derelict / outdoor-looking (categories DENY; tags DENY_TAGS when a tag map is given)."""
    out = {}
    for k, r in cat.items():
        if not r.get("complete"):
            continue
        if r["role"] == "env" and any(w in k for w in ENV_DENY):
            continue
        if r["role"] != "env" and (set(r.get("categories") or []) & DENY or set((tags or {}).get(k, [])) & DENY_TAGS):
            continue
        out[k] = r
    return out


def split_of(mid: str) -> str:
    u = int(hashlib.sha256(f"l8x-material:{mid}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "ood" if u < OOD_SHARE else "train"


def pick(cat: dict, role: str, seed: int, split: str = "train") -> dict:
    ids = sorted(k for k, r in cat.items() if r["role"] == role and split_of(k) == split)
    if not ids:
        raise ValueError(f"no {split} material for role {role}")
    h = int(hashlib.sha256(f"{role}:{int(seed)}".encode()).hexdigest()[:8], 16)
    return cat[ids[h % len(ids)]]


# ---------------------------------------------------------------------------------------------------- USD (pod)
def author(stage, path: str, rec: dict, root: str = ROOT, uv_scale=(1.0, 1.0)):
    """UsdPreviewSurface material at `path` from a texture record; -> UsdShade.Material."""
    from pxr import Gf, Sdf, UsdShade
    mat = UsdShade.Material.Define(stage, path)
    sh = UsdShade.Shader.Define(stage, path + "/PBR")
    sh.CreateIdAttr("UsdPreviewSurface")
    st = UsdShade.Shader.Define(stage, path + "/st")
    st.CreateIdAttr("UsdPrimvarReader_float2")
    st.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    tr = UsdShade.Shader.Define(stage, path + "/uv")
    tr.CreateIdAttr("UsdTransform2d")
    tr.CreateInput("in", Sdf.ValueTypeNames.Float2).ConnectToSource(st.ConnectableAPI(), "result")
    tr.CreateInput("scale", Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(*[float(v) for v in uv_scale]))

    def tex(name, key, cs, out, typ):
        t = UsdShade.Shader.Define(stage, f"{path}/{name}")
        t.CreateIdAttr("UsdUVTexture")
        t.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(os.path.join(root, rec["files"][key])))
        t.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set(cs)
        t.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        t.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        t.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(tr.ConnectableAPI(), "result")
        return t.CreateOutput(out, typ)
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        tex("diff", "diff", "sRGB", "rgb", Sdf.ValueTypeNames.Float3))
    if "rough" in rec["files"]:
        sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).ConnectToSource(
            tex("rough", "rough", "raw", "r", Sdf.ValueTypeNames.Float))
    if "nor_gl" in rec["files"]:
        t = tex("nor", "nor_gl", "raw", "rgb", Sdf.ValueTypeNames.Float3)
        tn = UsdShade.Shader.Get(stage, path + "/nor")
        tn.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2.0, 2.0, 2.0, 1.0))
        tn.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1.0, -1.0, -1.0, 0.0))
        sh.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(t)
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    return mat


def retexture(stage, path: str, rec: dict, root: str = ROOT, uv_scale=None) -> None:
    """Per-episode change WITHOUT a binding change: point an existing author() material's texture inputs (diffuse /
    roughness / normal) at another record's files (and optionally its UV scale). Bind once at scene setup (before
    the simulation starts), then call this per episode."""
    from pxr import Gf, Sdf, UsdShade
    for name, key in (("diff", "diff"), ("rough", "rough"), ("nor", "nor_gl")):
        sh = UsdShade.Shader.Get(stage, f"{path}/{name}")
        if sh and key in rec["files"]:
            sh.GetInput("file").Set(Sdf.AssetPath(os.path.join(root, rec["files"][key])))
    if uv_scale is not None:
        UsdShade.Shader.Get(stage, path + "/uv").GetInput("scale").Set(Gf.Vec2f(*[float(v) for v in uv_scale]))


def hdr_paths(cat: dict, split: str = "train", root: str = ROOT) -> list:
    """Absolute .hdr paths of the usable indoor HDRIs of a split (drop-in for a pool's hdr_maps)."""
    return [os.path.join(root, r["files"]["hdr"]) for k, r in sorted(cat.items())
            if r["role"] == "env" and split_of(k) == split]


def bind(prim, mat) -> None:
    from pxr import UsdShade
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat, UsdShade.Tokens.strongerThanDescendants)


def set_dome(stage, dome_path: str, rec: dict, intensity: float = 1000.0, root: str = ROOT) -> None:
    from pxr import Sdf, UsdLux
    dome = UsdLux.DomeLight(stage.GetPrimAtPath(dome_path))
    dome.CreateTextureFileAttr().Set(Sdf.AssetPath(os.path.join(root, rec["files"]["hdr"])))
    dome.CreateTextureFormatAttr().Set(UsdLux.Tokens.latlong)
    dome.CreateIntensityAttr().Set(float(intensity))
