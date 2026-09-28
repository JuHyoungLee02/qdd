"""Poly Haven models (CC0 1.0, https://polyhaven.com/license) for b4 (user-log 175): store / kitchen fixtures
(shelves, cabinets, display furniture) and product-like props (food, containers, bottles, jars, cans, boxes). Stdlib
only (pod). Downloads the 1k USD package (the .usdc + its included textures, md5 checked) of each selected model to
<out>/<id>/ and writes <out>/models.json (id, role fixture | product, name, categories, tags, authors, licence, usd).
Selection: role fixture = category shelves, or furniture with a shelf / cabinet / cupboard / rack / display /
kitchen / drawer / counter tag; role product = categories food / containers / dishes minus plants and tools.
usage: python tools/l8x_assets/polyhaven_models.py --out /data/harvest/assets_x/polyhaven_models [--dry]"""
from __future__ import annotations

import argparse
import json
import os

from polyhaven_fetch import API, LICENSE, fetch, get

FIXTURE_TAGS = {"shelf", "shelves", "cabinet", "cupboard", "rack", "display", "kitchen", "drawer", "drawers",
                "counter", "bookcase", "bookshelf", "sideboard", "dresser", "storage"}
PRODUCT_CATS = {"food", "containers", "dishes"}
NOT_PRODUCT = {"plants", "tools", "weapons", "firearms", "nature", "rocks", "trees", "ground cover"}


def role_of(info: dict):
    cats, tags = set(info.get("categories") or []), set(info.get("tags") or [])
    if ("shelves" in cats or ("furniture" in cats and tags & FIXTURE_TAGS)) and not cats & {"seating"}:
        return "fixture"
    if cats & PRODUCT_CATS and not cats & NOT_PRODUCT and "furniture" not in cats:
        return "product"
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--res", default="1k")
    a = ap.parse_args(argv)
    assets = json.loads(get(f"{API}/assets?t=models"))
    out = {}
    for aid in sorted(assets):
        info = assets[aid]
        role = role_of(info)
        if role is None:
            continue
        rec = {"id": aid, "role": role, "name": info.get("name"), "categories": info.get("categories"),
               "tags": info.get("tags"), "authors": sorted((info.get("authors") or {}).keys()), "license": LICENSE,
               "source": f"https://polyhaven.com/a/{aid}", "usd": None}
        if not a.dry:
            f = json.loads(get(f"{API}/files/{aid}")).get("usd", {}).get(a.res, {}).get("usd")
            if f:
                d = os.path.join(a.out, aid)
                ok = fetch(f["url"], f["md5"], os.path.join(d, os.path.basename(f["url"])))
                for rel, g in (f.get("include") or {}).items():
                    ok = ok and fetch(g["url"], g["md5"], os.path.join(d, rel))
                if ok:
                    rec["usd"] = os.path.join(aid, os.path.basename(f["url"]))
        out[aid] = rec
        print(role, aid, "ok" if (a.dry or rec["usd"]) else "NO_USD", flush=True)
    os.makedirs(a.out, exist_ok=True)
    json.dump({"license": LICENSE, "models": out}, open(os.path.join(a.out, "models.json"), "w"), indent=1)
    from collections import Counter
    print("DONE", dict(Counter(r["role"] for r in out.values())), flush=True)


if __name__ == "__main__":
    main()
