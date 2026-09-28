"""CC0 material library for the realistic bundle b4 (user-log 173): PBR textures (furniture wood, floors, walls,
fabric) and indoor HDR environment maps from Poly Haven (every asset CC0 1.0, https://polyhaven.com/license), via its
public API (api.polyhaven.com). Stdlib only (pod).
Per texture: 1k JPG diffuse / normal (OpenGL) / roughness; per HDRI: 2k .hdr. Selection: the API's categories, capped
per group, in id-hash order (deterministic, not alphabetical). Catalog <out>/materials.json: id, group, role
(furniture / floor / wall / fabric / env), files, authors, licence, source URL, md5 checked.
usage: python tools/l8x_assets/polyhaven_fetch.py --out /data/harvest/assets_x/materials [--dry]"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request

API = "https://api.polyhaven.com"
LICENSE = "CC0 1.0 (Poly Haven, https://polyhaven.com/license)"
GROUPS = {  # group: (asset type, API category, role, cap, required categories: any of)
    "wood": ("textures", "wood", "furniture", 28, ("man made", "indoor")),
    "floor": ("textures", "floor", "floor", 24, ("indoor",)),
    "wall": ("textures", "wall", "wall", 20, ("indoor", "plaster", "clean")),
    "tiles": ("textures", "tiles", "floor", 8, ()),
    "fabric": ("textures", "fabric", "fabric", 10, ()),
    "indoor": ("hdris", "indoor", "env", 40, ()),
}
TEX_MAPS = {"Diffuse": "diff", "nor_gl": "nor_gl", "Rough": "rough"}


def get(url: str, tries: int = 4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "qdd-l8x-assets"}),
                                        timeout=60) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(2 + 3 * k)


def fetch(url: str, md5: str, dst: str) -> bool:
    if os.path.exists(dst) and hashlib.md5(open(dst, "rb").read()).hexdigest() == md5:
        return True
    b = get(url)
    if hashlib.md5(b).hexdigest() != md5:
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst + ".part", "wb") as f:
        f.write(b)
    os.replace(dst + ".part", dst)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    cat, seen = {}, set()
    for group, (typ, category, role, cap, need) in GROUPS.items():
        assets = json.loads(get(f"{API}/assets?t={typ}&c={category}"))
        order = sorted(assets, key=lambda i: hashlib.sha256(f"b4:{i}".encode()).hexdigest())
        ids = [i for i in order if i not in seen and
               (not need or set(need) & set(assets[i].get("categories") or []))][:cap]
        for aid in ids:
            seen.add(aid)
            info = assets[aid]
            files = json.loads(get(f"{API}/files/{aid}"))
            rec = {"id": aid, "group": group, "role": role, "type": typ, "name": info.get("name"),
                   "authors": sorted((info.get("authors") or {}).keys()), "categories": info.get("categories"),
                   "license": LICENSE, "source": f"https://polyhaven.com/a/{aid}", "files": {}}
            if typ == "textures":
                want = {m: files.get(k, {}).get("1k", {}).get("jpg") for k, m in TEX_MAPS.items()}
                sub = os.path.join("textures", aid)
            else:
                want = {"hdr": files.get("hdri", {}).get("2k", {}).get("hdr")}
                sub = os.path.join("hdris", aid)
            ok = True
            for m, f in want.items():
                if not f:
                    ok = False
                    continue
                rel = os.path.join(sub, os.path.basename(f["url"]))
                if not a.dry and not fetch(f["url"], f["md5"], os.path.join(a.out, rel)):
                    ok = False
                    continue
                rec["files"][m] = rel
            rec["complete"] = ok
            cat[aid] = rec
            print(group, aid, "ok" if ok else "INCOMPLETE", flush=True)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "materials.json"), "w") as f:
        json.dump({"license": LICENSE, "source": "Poly Haven API", "groups": {g: v[2] for g, v in GROUPS.items()},
                   "materials": cat}, f, indent=1)
    from collections import Counter
    print("DONE", len(cat), dict(Counter(r["group"] for r in cat.values() if r["complete"])), flush=True)


if __name__ == "__main__":
    main()
