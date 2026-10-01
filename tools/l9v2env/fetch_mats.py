"""L9 v2 material + HDRI expansion (pod, stdlib; spec §12.3): every ambientCG material of a surface category (CC0)
and every Poly Haven HDRI (CC0) that the v1 library (harvest/l9/assets9/materials_l9.json) does not have. Files go
under --out (/data/harvest/assets_l9v2/materials); the table stores ABSOLUTE file paths (materials.author joins
root + path, an absolute path wins), so v1 and v2 records mix in one catalog. Record format = v1 (+ "setting" for
floors: indoor / outdoor ground, + "gen": "l9v2").
usage: python3 fetch_mats.py --code CODE_DIR --out /data/harvest/assets_l9v2/materials [--workers 12]"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ROLE = {  # ambientCG displayCategory (spaces removed) -> (role, setting); not listed = skipped (decals, food, signs)
    **{c: ("furniture", "indoor") for c in (
        "Wood", "Planks", "Metal", "PaintedMetal", "MetalPlates", "Plastic", "Marble", "Wicker", "Cardboard", "Paper",
        "Rubber", "Chipboard", "PaintedWood", "Porcelain", "Granite", "Onyx", "Bamboo", "Cork", "DiamondPlate",
        "CorrugatedSteel", "SheetMetal", "Styrofoam", "Foam", "Clay", "GlazedTerracotta", "Ivory", "Foil", "Rust",
        "Grate")},
    **{c: ("fabric", "indoor") for c in ("Fabric", "Leather", "Carpet", "Rope", "Net")},
    **{c: ("floor", "indoor") for c in ("Tiles", "WoodFloor", "Terrazzo", "Linoleum", "Travertine", "Tatami")},
    **{c: ("floor", "outdoor") for c in ("PavingStones", "Ground", "Gravel", "Asphalt", "Road", "Grass", "Moss",
                                          "ScatteredLeaves", "Pathway", "TactilePaving", "Rock", "Rocks",
                                          "MetalWalkway", "WoodChips")},
    **{c: ("wall", "indoor") for c in ("Plaster", "PaintedPlaster", "Wallpaper", "Bricks", "Concrete", "PaintedBricks",
                                        "OfficeCeiling", "Facade", "WoodSiding", "Paint", "AcousticFoam")},
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)
    sys.path.insert(0, a.code)
    from tools.l9.assets import materials_fetch as MF
    v1 = json.load(open(os.path.join(a.code, "harvest", "l9", "assets9", "materials_l9.json")))["materials"]
    os.makedirs(a.out, exist_ok=True)
    jobs = []
    hd = json.loads(MF.get(f"{MF.PH}/assets?t=hdris"))
    jobs += [(MF.ph_hdri, i, hd[i]) for i in sorted(hd) if f"ph_{i}" not in v1]
    acg = []
    for x in MF.acg_list():
        r = ROLE.get(str(x.get("displayCategory") or "").replace(" ", ""))
        if r and f"acg_{x['assetId']}" not in v1:
            acg.append((x, r))
    jobs += [(lambda aid, xr, out: dict(MF.acg_material(xr[0], xr[1][0], out), setting=xr[1][1]), x["assetId"], (x, r))
             for x, r in acg]
    print("JOBS", len(jobs), "hdri", sum(j[0] is MF.ph_hdri for j in jobs), "acg", len(acg), flush=True)

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
                r["files"] = {k: os.path.join(os.path.abspath(a.out), v) for k, v in r["files"].items()}
                r["gen"] = "l9v2"
                cat[r["id"]] = r
            if n % 100 == 0:
                print("progress", n, len(jobs), flush=True)
    with open(os.path.join(a.out, "materials_l9v2.json"), "w") as f:
        json.dump({"root": os.path.abspath(a.out), "license": "CC0 1.0 (Poly Haven / ambientCG)",
                   "source": "Poly Haven API + ambientCG API v2 (L9 v2 additions to materials_l9.json)",
                   "materials": cat}, f, separators=(",", ":"))
    ok = [r for r in cat.values() if r["complete"]]
    print("DONE", len(cat), "complete", len(ok), dict(Counter((r["type"], r["role"], r.get("setting")) for r in ok)),
          "sha", hashlib.sha256(json.dumps(sorted(cat)).encode()).hexdigest()[:12], flush=True)


if __name__ == "__main__":
    main()
