"""L9 v2 decor meshes from Amazon Berkeley Objects (ABO, CC BY 4.0, https://amazon-berkeley-objects.s3.amazonaws.com/
index.html: "All models are distributed under Creative Commons Attribution 4.0 International License"; credit
Amazon.com): download the glTF 2.0 binary of real products (furniture, lamps, vases, planters, rugs, storage ...),
convert to a render-only USD (pure python glb reader -> UsdGeom.Mesh + UsdPreviewSurface, transforms baked, Y-up ->
Z-up, metres, origin = bbox bottom-centre, textures downsized to 1k) and write decor rows (the decor_ph.json format:
dst, collider_size = render bbox, origin_offset 0, kind floor | tabletop, category = product type, license, source).
Pod, pylib python (pxr + numpy + Pillow):
  PYTHONPATH=/data/harvest/assets_x/pylib:/data/harvest/pylib python3 abo_decor.py --out DIR [--max 3000] [--workers 4]"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import struct
import time
import urllib.request
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

BASE = "https://amazon-berkeley-objects.s3.amazonaws.com"
LIC = "CC BY 4.0 (Amazon Berkeley Objects, credit Amazon.com; https://creativecommons.org/licenses/by/4.0/)"
SKIP_TYPES = {"CELLULAR_PHONE_CASE", "SHOES", "BOOT", "SANDAL", "SHIRT", "PANTS", "DRESS", "HANDBAG", "LUGGAGE",
              "WATCH", "JEWELRY", "EARRING", "NECKLACE", "RING", "SUNGLASSES", "HAT", "BACKPACK", "AUTO_ACCESSORY",
              "WALL_ART", "SOUND_AND_RECORDING_EQUIPMENT"}
TEX_MAX = 1024
CT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def get(url: str, tries: int = 5) -> bytes:
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "qdd-l9v2-abo"}),
                                        timeout=300) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(3 + 5 * k)


def product_types() -> dict:
    """3dmodel_id -> (product_type, english item name) from the listings metadata."""
    out = {}
    for h in "0123456789abcdef":
        for ln in gzip.decompress(get(f"{BASE}/listings/metadata/listings_{h}.json.gz")).decode().splitlines():
            r = json.loads(ln)
            mid = r.get("3dmodel_id")
            if not mid:
                continue
            pt = ((r.get("product_type") or [{}])[0]).get("value", "")
            name = next((x["value"] for x in r.get("item_name") or [] if str(x.get("language_tag", "")).startswith("en")),
                        "")
            out[mid] = (pt, name[:120])
    return out


# ------------------------------------------------------------------------------------------------ glb -> usd
def read_glb(b: bytes):
    import numpy as np
    magic, _, _ = struct.unpack_from("<III", b, 0)
    if magic != 0x46546C67:
        raise ValueError("not glb")
    off, js, binc = 12, None, b""
    while off < len(b):
        ln, typ = struct.unpack_from("<II", b, off)
        data = b[off + 8: off + 8 + ln]
        if typ == 0x4E4F534A:
            js = json.loads(data)
        elif typ == 0x004E4942:
            binc = data
        off += 8 + ln

    def view(i):
        v = js["bufferViews"][i]
        o = v.get("byteOffset", 0)
        return binc[o: o + v["byteLength"]], v.get("byteStride")

    def acc(i):
        a = js["accessors"][i]
        raw, stride = view(a["bufferView"])
        n, c, t = a["count"], NC[a["type"]], CT[a["componentType"]]
        sz = struct.calcsize(t)
        o = a.get("byteOffset", 0)
        dt = np.dtype("<" + t)
        if stride and stride != sz * c:
            arr = np.stack([np.frombuffer(raw, dt, c, o + k * stride) for k in range(n)])
        else:
            arr = np.frombuffer(raw, dt, n * c, o).reshape(n, c)
        arr = arr.astype(np.float64)
        if a.get("normalized") and t in "BH":
            arr /= float(np.iinfo(dt).max)
        return arr

    return js, view, acc


def node_mats(js):
    import numpy as np

    def local(n):
        if "matrix" in n:
            return np.array(n["matrix"], float).reshape(4, 4).T
        T = np.eye(4)
        if "scale" in n:
            T = np.diag([*n["scale"], 1.0]) @ T
        if "rotation" in n:
            x, y, z, w = n["rotation"]
            R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                          [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                          [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
            M = np.eye(4)
            M[:3, :3] = R
            T = M @ T
        if "translation" in n:
            M = np.eye(4)
            M[:3, 3] = n["translation"]
            T = M @ T
        return T

    out = []

    def walk(i, P):
        n = js["nodes"][i]
        W = P @ local(n)
        if "mesh" in n:
            out.append((n["mesh"], W))
        for c in n.get("children", []):
            walk(c, W)

    sc = js.get("scenes", [{"nodes": list(range(len(js.get("nodes", []))))}])[js.get("scene", 0)]
    for i in sc["nodes"]:
        walk(i, np.eye(4))
    return out


def convert(glb: bytes, dst_dir: str, name: str) -> dict:
    import numpy as np
    from PIL import Image
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt
    js, view, acc = read_glb(glb)
    os.makedirs(dst_dir, exist_ok=True)
    Y2Z = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
    prims = []
    for mi, W in node_mats(js):
        for p in js["meshes"][mi]["primitives"]:
            if p.get("mode", 4) != 4 or "POSITION" not in p["attributes"]:
                continue
            P = acc(p["attributes"]["POSITION"])
            M = Y2Z @ W
            P = (P @ M[:3, :3].T) + M[:3, 3]
            N = acc(p["attributes"]["NORMAL"]) if "NORMAL" in p["attributes"] else None
            if N is not None:
                Nm = np.linalg.inv(M[:3, :3]).T
                N = N @ Nm.T
                N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
            UV = acc(p["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in p["attributes"] else None
            I = acc(p["indices"]).astype(np.int64).ravel() if "indices" in p else np.arange(len(P))
            prims.append((P, N, UV, I, p.get("material")))
    if not prims:
        raise ValueError("no triangles")
    allP = np.concatenate([q[0] for q in prims])
    lo, hi = allP.min(0), allP.max(0)
    off = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    texcache = {}

    def tex_file(ti):
        if ti in texcache:
            return texcache[ti]
        src = js["textures"][ti]["source"]
        img = js["images"][src]
        raw, _ = view(img["bufferView"])
        im = Image.open(io.BytesIO(raw))
        im.thumbnail((TEX_MAX, TEX_MAX))
        fn = f"t{src}.png"
        im.save(os.path.join(dst_dir, fn))
        texcache[ti] = fn
        return fn

    dst = os.path.join(dst_dir, f"{name}.usdc")
    if os.path.exists(dst):
        os.remove(dst)
    st = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(st, "/Piece")
    st.SetDefaultPrim(root.GetPrim())
    mats = {}

    def material(mi):
        if mi in mats:
            return mats[mi]
        path = f"/Piece/Looks/m{len(mats)}"
        mat = UsdShade.Material.Define(st, path)
        sh = UsdShade.Shader.Define(st, path + "/PBR")
        sh.CreateIdAttr("UsdPreviewSurface")
        m = js["materials"][mi] if mi is not None and "materials" in js else {}
        pbr = m.get("pbrMetallicRoughness", {})
        rd = UsdShade.Shader.Define(st, path + "/st")
        rd.CreateIdAttr("UsdPrimvarReader_float2")
        rd.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")

        def tx(nm, ti, cs):
            t = UsdShade.Shader.Define(st, f"{path}/{nm}")
            t.CreateIdAttr("UsdUVTexture")
            t.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("./" + tex_file(ti)))
            t.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set(cs)
            t.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(rd.ConnectableAPI(), "result")
            return t

        bc = pbr.get("baseColorFactor", [0.8, 0.8, 0.8, 1.0])
        if "baseColorTexture" in pbr:
            t = tx("diff", pbr["baseColorTexture"]["index"], "sRGB")
            t.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(*[float(v) for v in bc]))
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                t.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
        else:
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*[float(v) for v in bc[:3]]))
        if "metallicRoughnessTexture" in pbr:
            t = tx("mr", pbr["metallicRoughnessTexture"]["index"], "raw")
            sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).ConnectToSource(
                t.CreateOutput("g", Sdf.ValueTypeNames.Float))
            sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).ConnectToSource(
                t.CreateOutput("b", Sdf.ValueTypeNames.Float))
        else:
            sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(pbr.get("roughnessFactor", 0.6)))
            sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(pbr.get("metallicFactor", 0.0)))
        if "normalTexture" in m:
            t = tx("nor", m["normalTexture"]["index"], "raw")
            t.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2.0, 2.0, 2.0, 1.0))
            t.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1.0, -1.0, -1.0, 0.0))
            sh.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(
                t.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        mats[mi] = mat
        return mat

    nt = 0
    for k, (P, N, UV, I, mi) in enumerate(prims):
        g = UsdGeom.Mesh.Define(st, f"/Piece/g{k}")
        g.CreatePointsAttr(Vt.Vec3fArray.FromNumpy((P - off).astype("float32")))
        g.CreateFaceVertexCountsAttr(Vt.IntArray([3] * (len(I) // 3)))
        g.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(I[: len(I) // 3 * 3].astype("int32")))
        g.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        if N is not None:
            g.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(N.astype("float32")))
            g.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        if UV is not None:
            uv = UV.copy()
            uv[:, 1] = 1.0 - uv[:, 1]
            pv = UsdGeom.PrimvarsAPI(g).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
            pv.Set(Vt.Vec2fArray.FromNumpy(uv.astype("float32")))
        UsdShade.MaterialBindingAPI.Apply(g.GetPrim()).Bind(material(mi))
        nt += len(I) // 3
    st.GetRootLayer().Save()
    return {"dst": dst, "size": [round(float(v), 4) for v in hi - lo], "tris": int(nt)}


def one(args):
    mid, path, out = args
    d = os.path.join(out, "models", mid)
    try:
        if os.path.exists(os.path.join(d, "row.json")):
            return mid, json.load(open(os.path.join(d, "row.json")))
        r = convert(get(f"{BASE}/3dmodels/original/{path}"), d, mid)
        json.dump(r, open(os.path.join(d, "row.json"), "w"))
        return mid, r
    except Exception as e:  # noqa: BLE001
        return mid, {"error": f"{type(e).__name__}: {e}"[:200]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    meta = gzip.decompress(get(f"{BASE}/3dmodels/metadata/3dmodels.csv.gz")).decode().splitlines()
    head = meta[0].split(",")
    rows = [dict(zip(head, ln.split(","))) for ln in meta[1:] if ln.strip()]
    pt = product_types()
    json.dump(pt, open(os.path.join(a.out, "product_types.json"), "w"))
    sel = []
    for r in rows:
        ex = [float(r["extent_x"]), float(r["extent_y"]), float(r["extent_z"])]
        typ = pt.get(r["3dmodel_id"], ("", ""))[0]
        if typ in SKIP_TYPES or max(ex) > 2.4 or max(ex) < 0.05 or int(r["faces"]) > 400000:
            continue
        sel.append(r)
    sel.sort(key=lambda r: hashlib.sha256(f"l9v2abo:{r['3dmodel_id']}".encode()).hexdigest())
    sel = sel[: a.max]
    print("models", len(rows), "selected", len(sel), Counter(pt.get(r["3dmodel_id"], ("?",))[0] for r in sel).most_common(25),
          flush=True)
    out, drop = {}, {}
    with ProcessPoolExecutor(a.workers) as ex:
        for n, (mid, r) in enumerate(ex.map(one, [(r["3dmodel_id"], r["path"], a.out) for r in sel], chunksize=4)):
            if "error" in r:
                drop[mid] = r["error"]
                continue
            sx, sy, sz = r["size"]
            typ, name = pt.get(mid, ("", ""))
            floor = sz >= 0.40 or max(sx, sy) >= 0.60
            split = "ood" if int(hashlib.sha256(f"l9v2abo:{mid}".encode()).hexdigest()[:8], 16) % 5 == 0 else "train"
            out[f"abo_{mid}"] = {"dst": r["dst"], "collider_size": r["size"], "render_size": r["size"],
                                 "origin_offset": [0.0, 0.0, 0.0], "yaw": 0.0, "kind": "floor" if floor else "tabletop",
                                 "category": (typ or "abo").lower(), "item_name": name, "license": LIC,
                                 "source": f"{BASE}/3dmodels/original/ (ABO 3dmodel_id {mid})",
                                 "attribution": "Amazon Berkeley Objects, Amazon.com", "split": split,
                                 "visual_only": True, "tris": r["tris"]}
            if n % 100 == 0:
                print("progress", n, len(sel), flush=True)
    json.dump({"license": LIC, "source": "Amazon Berkeley Objects 3D models (glb -> usd, tools/l9v2env/abo_decor.py)",
               "assets": out, "dropped": drop}, open(os.path.join(a.out, "decor_abo.json"), "w"), indent=1)
    print("DONE", len(out), Counter(r["kind"] for r in out.values()), "dropped", len(drop), flush=True)


if __name__ == "__main__":
    main()
