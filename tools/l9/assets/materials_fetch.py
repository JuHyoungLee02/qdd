"""L9 material + HDRI library (spec 2026-09-30 §5): every Poly Haven texture (CC0) + a capped, indoor-leaning
ambientCG material set (CC0) + Poly Haven HDRIs (all indoor, outdoor capped). Stdlib only (pod).
Record format = harvest/sim/assets_x/materials.json (id, group, role furniture|floor|wall|fabric|env, type, name,
authors, categories, license, source, files rel. to --out, complete) plus "provider" and, for HDRIs, "setting".
Per texture 1k JPG diff / nor_gl / rough; per HDRI 2k .hdr.
usage: python tools/l9/assets/materials_fetch.py --out /data/harvest/assets_l9/materials [--acg-cap 450]
       [--hdri-outdoor-cap 200] [--workers 16]"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

PH = "https://api.polyhaven.com"
ACG = "https://ambientcg.com/api/v2/full_json"
LIC_PH = "CC0 1.0 (Poly Haven, https://polyhaven.com/license)"
LIC_ACG = "CC0 1.0 (ambientCG, https://docs.ambientcg.com/license/)"
TEX_MAPS = {"Diffuse": "diff", "nor_gl": "nor_gl", "Rough": "rough"}
ACG_MAPS = {"_Color.": "diff", "_NormalGL.": "nor_gl", "_Roughness.": "rough"}
# ambientCG displayCategory -> role (None = skip: outdoor terrain / decals / not a surface material)
ACG_ROLE = {
    "Wood": "furniture", "Planks": "furniture", "Wood Floor": "floor", "Metal": "furniture",
    "Painted Metal": "furniture", "Metal Plates": "furniture", "Plastic": "furniture", "Marble": "furniture",
    "Leather": "fabric", "Fabric": "fabric", "Carpet": "fabric", "Wicker": "furniture", "Cardboard": "furniture",
    "Paper": "furniture", "Rubber": "furniture", "Chipboard": "furniture", "Painted Wood": "furniture",
    "Tiles": "floor", "Terrazzo": "floor", "Linoleum": "floor", "Travertine": "floor", "Porcelain": "furniture",
    "Plaster": "wall", "Painted Plaster": "wall", "Wallpaper": "wall", "Bricks": "wall", "Concrete": "wall",
    "Paving Stones": "floor", "Granite": "furniture", "Onyx": "furniture", "Facade": "wall", "Bamboo": "furniture",
    "Tatami": "floor", "Cork": "furniture", "Painted Bricks": "wall", "Office Ceiling": "wall",
}


def get(url: str, tries: int = 5) -> bytes:
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "qdd-l9-assets"}),
                                        timeout=120) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(2 + 3 * k)


def fetch(url: str, md5: str | None, dst: str) -> bool:
    if os.path.exists(dst) and (md5 is None or hashlib.md5(open(dst, "rb").read()).hexdigest() == md5):
        return True
    b = get(url)
    if md5 is not None and hashlib.md5(b).hexdigest() != md5:
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst + ".part", "wb") as f:
        f.write(b)
    os.replace(dst + ".part", dst)
    return True


def ph_role(cats: list[str]) -> str:
    c = set(cats)
    if c & {"fabric", "leather", "carpet"}:
        return "fabric"
    if c & {"floor", "tiles"}:
        return "floor"
    if c & {"wall", "brick", "plaster", "concrete"}:
        return "wall"
    if c & {"wood", "metal", "plastic", "man made"}:
        return "furniture"
    return "floor"  # terrain / rock / sand / asphalt: ground-like


def ph_texture(aid: str, info: dict, out: str) -> dict:
    files = json.loads(get(f"{PH}/files/{aid}"))
    cats = info.get("categories") or []
    rec = {"id": f"ph_{aid}", "provider": "polyhaven", "group": (cats[0] if cats else "misc"), "role": ph_role(cats),
           "type": "textures", "name": info.get("name"), "authors": sorted((info.get("authors") or {}).keys()),
           "categories": cats, "indoor": "indoor" in cats, "license": LIC_PH,
           "source": f"https://polyhaven.com/a/{aid}", "files": {}}
    ok = True
    for k, m in TEX_MAPS.items():
        f = files.get(k, {}).get("1k", {}).get("jpg")
        if not f:
            ok = False
            continue
        rel = os.path.join("textures", aid, os.path.basename(f["url"]))
        if not fetch(f["url"], f["md5"], os.path.join(out, rel)):
            ok = False
            continue
        rec["files"][m] = rel
    rec["complete"] = ok
    return rec


def ph_hdri(aid: str, info: dict, out: str) -> dict:
    files = json.loads(get(f"{PH}/files/{aid}"))
    cats = info.get("categories") or []
    rec = {"id": f"ph_{aid}", "provider": "polyhaven", "group": "hdri", "role": "env", "type": "hdris",
           "setting": "indoor" if "indoor" in cats else "outdoor", "name": info.get("name"),
           "authors": sorted((info.get("authors") or {}).keys()), "categories": cats, "license": LIC_PH,
           "source": f"https://polyhaven.com/a/{aid}", "files": {}}
    f = files.get("hdri", {}).get("2k", {}).get("hdr")
    ok = bool(f)
    if f:
        rel = os.path.join("hdris", aid, os.path.basename(f["url"]))
        ok = fetch(f["url"], f["md5"], os.path.join(out, rel))
        if ok:
            rec["files"]["hdr"] = rel
    rec["complete"] = ok
    return rec


def acg_list() -> list[dict]:
    res, off = [], 0
    while True:
        d = json.loads(get(f"{ACG}?type=Material&include=downloadData,tagData&limit=250&offset={off}"))
        res += d["foundAssets"]
        off += 250
        if off >= int(d["numberOfResults"]) or not d["foundAssets"]:
            return res


def acg_material(a: dict, role: str, out: str) -> dict:
    aid = a["assetId"]
    rec = {"id": f"acg_{aid}", "provider": "ambientcg", "group": a.get("displayCategory"), "role": role,
           "type": "textures", "name": a.get("displayName") or aid, "authors": ["ambientCG (Lennart Demes)"],
           "categories": a.get("tags") or [], "indoor": True, "license": LIC_ACG,
           "source": f"https://ambientcg.com/a/{aid}", "files": {}}
    url = None
    for fol in (a.get("downloadFolders") or {}).values():
        for cat in (fol.get("downloadFiletypeCategories") or {}).values():
            for dl in cat.get("downloads") or []:
                if dl.get("attribute") == "1K-JPG":
                    url = dl.get("fullDownloadPath") or dl.get("downloadLink")
    ok = url is not None
    if ok:
        sub = os.path.join("textures_acg", aid)
        want = {m: os.path.join(sub, f"{aid}_1K-JPG{suf}jpg") for suf, m in ACG_MAPS.items()}
        if not all(os.path.exists(os.path.join(out, p)) for p in want.values()):
            z = zipfile.ZipFile(io.BytesIO(get(url)))
            os.makedirs(os.path.join(out, sub), exist_ok=True)
            for n in z.namelist():
                for suf, m in ACG_MAPS.items():
                    if suf in n and n.endswith(".jpg"):
                        with open(os.path.join(out, want[m]), "wb") as f:
                            f.write(z.read(n))
        for m, p in want.items():
            if os.path.exists(os.path.join(out, p)):
                rec["files"][m] = p
        ok = len(rec["files"]) == 3
    rec["complete"] = ok
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--acg-cap", type=int, default=450)
    ap.add_argument("--hdri-outdoor-cap", type=int, default=200)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    jobs = []
    tex = json.loads(get(f"{PH}/assets?t=textures"))
    jobs += [(ph_texture, i, tex[i]) for i in sorted(tex)]
    hd = json.loads(get(f"{PH}/assets?t=hdris"))
    order = sorted(hd, key=lambda i: hashlib.sha256(f"l9:{i}".encode()).hexdigest())
    indoor = [i for i in order if "indoor" in (hd[i].get("categories") or [])]
    outdoor = [i for i in order if i not in set(indoor)][:a.hdri_outdoor_cap]
    jobs += [(ph_hdri, i, hd[i]) for i in indoor + outdoor]
    acg = [x for x in acg_list() if ACG_ROLE.get(x.get("displayCategory"))]
    acg.sort(key=lambda x: hashlib.sha256(f"l9:{x['assetId']}".encode()).hexdigest())
    percat: dict[str, int] = {}
    cap_cat = max(8, a.acg_cap // 12)
    sel = []
    for x in acg:
        c = x["displayCategory"]
        if percat.get(c, 0) < cap_cat and len(sel) < a.acg_cap:
            percat[c] = percat.get(c, 0) + 1
            sel.append(x)
    jobs += [(lambda aid, x, out: acg_material(x, ACG_ROLE[x["displayCategory"]], out), x["assetId"], x)
             for x in sel]
    print("JOBS", len(jobs), "ph_tex", len(tex), "hdri", len(indoor), "+", len(outdoor), "acg", len(sel), flush=True)

    def run(j):
        fn, aid, info = j
        try:
            return fn(aid, info, a.out)
        except Exception as e:  # noqa: BLE001
            print("ERR", aid, repr(e)[:200], flush=True)
            return None

    cat = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for n, r in enumerate(ex.map(run, jobs)):
            if r:
                cat[r["id"]] = r
            if n % 100 == 0:
                print("progress", n, len(jobs), flush=True)
    with open(os.path.join(a.out, "materials_l9.json"), "w") as f:
        json.dump({"root": os.path.abspath(a.out), "license": "CC0 1.0 (Poly Haven / ambientCG)",
                   "source": "Poly Haven API + ambientCG API v2", "materials": cat}, f, separators=(",", ":"))
    from collections import Counter
    ok = [r for r in cat.values() if r["complete"]]
    print("DONE", len(cat), "complete", len(ok), dict(Counter((r["type"], r["role"]) for r in ok)), flush=True)


if __name__ == "__main__":
    main()
