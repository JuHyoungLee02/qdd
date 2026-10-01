"""Poly Haven decor rows re-made from the glTF 1k files (CC0) with the ABO converter (tools/l9v2env/abo_decor.convert:
UsdPreviewSurface, transforms baked, Z-up, bottom-centre origin). Why: the Poly Haven USD files carry Blender
MaterialX node graphs (render smoke 2026-10-02: +4.4 min MDL compile per Isaac start, textures referenced at
/mnt/prod/... missing). Rewrites decor_ph.json (same ids / kinds / splits, new dst).
Pod, pylib python: PYTHONPATH=/data/harvest/assets_x/pylib:/data/harvest/pylib python3 ph_gltf.py --dir DECOR_DIR"""
from __future__ import annotations

import argparse
import json
import os
import struct
from concurrent.futures import ProcessPoolExecutor

PH = "https://api.polyhaven.com"


def to_glb(js: dict, buffers: list, images: dict) -> bytes:
    """A glTF (json + its buffers + image bytes by uri) packed as one glb (one buffer)."""
    blob = bytearray()
    offs = []
    for b in buffers:
        offs.append(len(blob))
        blob += b
        blob += b"\0" * (-len(blob) % 4)
    for v in js.get("bufferViews", []):
        v["byteOffset"] = v.get("byteOffset", 0) + offs[v.get("buffer", 0)]
        v["buffer"] = 0
    for im in js.get("images", []):
        if "uri" in im:
            data = images[im.pop("uri")]
            js.setdefault("bufferViews", []).append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)})
            im["bufferView"] = len(js["bufferViews"]) - 1
            blob += data
            blob += b"\0" * (-len(blob) % 4)
    js["buffers"] = [{"byteLength": len(blob)}]
    j = json.dumps(js).encode()
    j += b" " * (-len(j) % 4)
    return (struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(blob)) + struct.pack("<II", len(j), 0x4E4F534A)
            + j + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob))


def one(args):
    aid, out = args
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import abo_decor as AB
    d = os.path.join(out, "models_gltf", aid)
    try:
        if os.path.exists(os.path.join(d, "row.json")):
            return aid, json.load(open(os.path.join(d, "row.json")))
        f = json.loads(AB.get(f"{PH}/files/{aid}"))["gltf"]["1k"]["gltf"]
        js = json.loads(AB.get(f["url"]))
        inc = {k: AB.get(v["url"]) for k, v in (f.get("include") or {}).items()}
        bufs = [inc[b["uri"]] for b in js.get("buffers", [])]
        r = AB.convert(to_glb(js, bufs, inc), d, aid)
        json.dump(r, open(os.path.join(d, "row.json"), "w"))
        return aid, r
    except Exception as e:  # noqa: BLE001
        return aid, {"error": f"{type(e).__name__}: {e}"[:200]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    tab = json.load(open(os.path.join(a.dir, "decor_ph.json")))
    ids = [k[3:] for k in tab["assets"]]
    rows, drop = {}, dict(tab.get("dropped", {}))
    with ProcessPoolExecutor(a.workers) as ex:
        for aid, r in ex.map(one, [(i, a.dir) for i in ids]):
            k = f"ph_{aid}"
            if "error" in r:
                drop[aid] = r["error"]
                continue
            rows[k] = dict(tab["assets"][k], dst=r["dst"], collider_size=r["size"], render_size=r["size"],
                           origin_offset=[0.0, 0.0, 0.0], converted="gltf->usd (abo_decor.convert)", tris=r["tris"])
    tab["assets"], tab["dropped"] = rows, drop
    tab["source"] = "Poly Haven models API (gltf 1k -> usd, tools/l9v2env/ph_gltf.py)"
    json.dump(tab, open(os.path.join(a.dir, "decor_ph.json"), "w"), indent=1)
    print("DONE", len(rows), "dropped", len(drop), flush=True)


if __name__ == "__main__":
    main()
