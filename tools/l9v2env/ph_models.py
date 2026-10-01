"""L9 v2 decor meshes from Poly Haven models (CC0, https://polyhaven.com/license): download the 1k USD of every
model in an indoor-ish category, wrap it as a render-only piece (/Piece/norm/yup -> the model; origin = bbox
bottom-centre, metres, Z up) and write rows for world9 decor (the furniture_mesh row format: dst, collider_size
(= render bbox), origin_offset (0 after the wrap), category, license, source + kind floor | tabletop, split).
Pod, pylib python (pxr): PYTHONPATH=/data/harvest/assets_x/pylib python3 ph_models.py --out DIR [--workers 8]"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

PH = "https://api.polyhaven.com"
LIC = "CC0 1.0 (Poly Haven, https://polyhaven.com/license)"
KEEP = {"furniture", "seating", "table", "decorative", "props", "plants", "lighting", "electronics", "containers",
        "appliances", "tools", "kitchen", "food", "shelves", "storage", "office", "books", "toys", "bathroom"}
DROP = {"rocks", "ground cover", "trees", "structures", "vehicles", "weapons", "architecture", "buildings",
        "terrain", "cliffs", "scan"}
MAX_SIDE, MIN_SIDE = 2.4, 0.04


def get(url: str, tries: int = 5) -> bytes:
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "qdd-l9v2-models"}),
                                        timeout=180) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(2 + 3 * k)


def fetch(url: str, md5: str | None, dst: str) -> None:
    if os.path.exists(dst) and (md5 is None or hashlib.md5(open(dst, "rb").read()).hexdigest() == md5):
        return
    b = get(url)
    if md5 is not None and hashlib.md5(b).hexdigest() != md5:
        raise ValueError(f"md5 {url}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst + ".part", "wb") as f:
        f.write(b)
    os.replace(dst + ".part", dst)


def download(aid: str, out: str) -> str:
    files = json.loads(get(f"{PH}/files/{aid}"))
    u = files["usd"]["1k"]["usd"]
    d = os.path.join(out, "models", aid)
    main = os.path.join(d, os.path.basename(u["url"]))
    fetch(u["url"], u.get("md5"), main)
    for rel, f in (u.get("include") or {}).items():
        fetch(f["url"], f.get("md5"), os.path.join(d, rel))
    return main


def wrap(src: str) -> dict:
    from pxr import Usd, UsdGeom
    st = Usd.Stage.Open(src)
    mpu, up = float(UsdGeom.GetStageMetersPerUnit(st)), str(UsdGeom.GetStageUpAxis(st))
    r = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(st.GetPseudoRoot()) \
        .ComputeAlignedRange()
    lo, hi = [float(v) * mpu for v in r.GetMin()], [float(v) * mpu for v in r.GetMax()]
    if up == "Y":  # rotateX +90: (x, y, z) -> (x, -z, y)
        lo, hi = [lo[0], -hi[2], lo[1]], [hi[0], -lo[2], hi[1]]
    size = [hi[i] - lo[i] for i in range(3)]
    dst = os.path.splitext(src)[0] + "_piece.usda"
    if os.path.exists(dst):
        os.remove(dst)
    w = Usd.Stage.CreateNew(dst)
    UsdGeom.SetStageMetersPerUnit(w, 1.0)
    UsdGeom.SetStageUpAxis(w, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(w, "/Piece")
    w.SetDefaultPrim(root.GetPrim())
    norm = UsdGeom.Xform.Define(w, "/Piece/norm")
    norm.AddTranslateOp().Set((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
    yup = UsdGeom.Xform.Define(w, "/Piece/norm/yup")
    if up == "Y":
        yup.AddRotateXOp().Set(90.0)
    if abs(mpu - 1.0) > 1e-9:
        yup.AddScaleOp().Set((mpu, mpu, mpu))
    yup.GetPrim().GetReferences().AddReference(os.path.basename(src))
    w.GetRootLayer().Save()
    return {"dst": dst, "size": [round(v, 4) for v in size], "meters_per_unit": mpu, "up_axis": up}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    allm = json.loads(get(f"{PH}/assets?t=models"))
    sel = {k: v for k, v in allm.items() if set(c.lower() for c in v.get("categories") or []) & KEEP
           and not set(c.lower() for c in v.get("categories") or []) & DROP}
    print("models", len(allm), "selected", len(sel), flush=True)

    def one(aid):
        try:
            return aid, wrap(download(aid, a.out))
        except Exception as e:  # noqa: BLE001
            return aid, {"error": f"{type(e).__name__}: {e}"[:200]}

    rows, drop = {}, {}
    with ThreadPoolExecutor(a.workers) as ex:
        for n, (aid, r) in enumerate(ex.map(one, sorted(sel))):
            if "error" in r:
                drop[aid] = r["error"]
                continue
            sx, sy, sz = r["size"]
            if max(sx, sy, sz) > MAX_SIDE or max(sx, sy, sz) < MIN_SIDE:
                drop[aid] = f"size {r['size']}"
                continue
            info = sel[aid]
            cats = [c.lower() for c in info.get("categories") or []]
            floor = sz >= 0.35 or bool(set(cats) & {"furniture", "seating", "table", "shelves", "storage"}) and sz >= 0.25
            split = "ood" if int(hashlib.sha256(f"l9v2ph:{aid}".encode()).hexdigest()[:8], 16) % 5 == 0 else "train"
            rows[f"ph_{aid}"] = {"dst": r["dst"], "collider_size": r["size"], "render_size": r["size"],
                                 "origin_offset": [0.0, 0.0, 0.0], "yaw": 0.0, "kind": "floor" if floor else "tabletop",
                                 "category": next((c for c in cats if c in KEEP), "props"), "categories": cats,
                                 "authors": sorted((info.get("authors") or {}).keys()), "license": LIC,
                                 "source": f"https://polyhaven.com/a/{aid}", "split": split, "visual_only": True,
                                 "meters_per_unit": r["meters_per_unit"], "up_axis": r["up_axis"]}
            if n % 50 == 0:
                print("progress", n, len(sel), flush=True)
    json.dump({"license": LIC, "source": "Poly Haven models API (usd 1k)", "assets": rows, "dropped": drop},
              open(os.path.join(a.out, "decor_ph.json"), "w"), indent=1)
    print("DONE", len(rows), Counter(r["kind"] for r in rows.values()), Counter(r["category"] for r in rows.values()),
          "dropped", len(drop), flush=True)


if __name__ == "__main__":
    main()
