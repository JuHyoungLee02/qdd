"""L9 v2 collider quality of the catalog objects (pxr + numpy + scipy, no SimulationApp; Isaac python):
does the physics collider (the explicit `*_collider<i>` convex-hull meshes of the physics USD) leave the cavity of a
hollow object free, so that one finger can go inside for a rim / wall pinch?

Per object (canonical frame, as tools/l9/mesh_export.py): the open cavity from the render mesh (vertical ray at the
bbox centre from above: first hit = inner floor; depth >= 1.5 cm = open), its inner radius (horizontal rays at mid
cavity depth, min of 8 directions), then probe points (axis + rings at 0.5 r_in and r_in - 7 mm, 3 heights) tested
against the collider hulls: filled_axis / filled_wall = fraction of probe points inside any hull.
  verdict: not_hollow | ok (filled_wall <= 0.2) | bad (filled_wall > 0.2: a finger cannot go inside the wall)
  python tools/l9/collider_report.py --rows rows.json --meshes DIR --out DIR [--shard i/n]
Writes <out>/collider_<i>.jsonl; merge with --merge -> <out>/collider_report.json."""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import grasp9 as G  # noqa: E402
from tools.l9.mesh_export import qmat  # noqa: E402

MIN_DEPTH = 0.015
WALL_IN = 0.007


def colliders(usd_path: str, body_rel: str):
    """[(name, approximation, points (N,3) in the body frame)] of the collision meshes (physics poses: no scale)."""
    from pxr import Usd, UsdGeom, UsdPhysics
    st = Usd.Stage.Open(usd_path)
    dp = st.GetDefaultPrim()
    cache = UsdGeom.XformCache()
    body = st.GetPrimAtPath(dp.GetPath().AppendPath(body_rel)) if body_rel else dp
    if not body or not body.IsValid():
        body = dp
    Mb = np.array(cache.GetLocalToWorldTransform(body), float).T
    U, _, Vt = np.linalg.svd(Mb[:3, :3])
    Rb, tb = U @ Vt, Mb[:3, 3]
    out = []
    for p in Usd.PrimRange(dp):
        if not p.IsA(UsdGeom.Mesh) or not p.HasAPI(UsdPhysics.CollisionAPI):
            continue
        en = UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get()
        if en is False:
            continue
        ap = UsdPhysics.MeshCollisionAPI(p).GetApproximationAttr().Get() if p.HasAPI(UsdPhysics.MeshCollisionAPI) else None
        pts = UsdGeom.Mesh(p).GetPointsAttr().Get()
        if pts is None or len(pts) < 4:
            continue
        M = np.array(cache.GetLocalToWorldTransform(p), float).T
        Pw = np.asarray(pts, float) @ M[:3, :3].T + M[:3, 3]
        out.append((p.GetName(), str(ap), (Pw - tb) @ Rb))
    return out


def to_canonical(P, row):
    cx, cy = row.get("centre_from_root_xy", (0.0, 0.0))
    off = np.array([cx, cy, float(row["height"]) / 2 - float(row["root_above_bottom"])])
    return P @ qmat(row["spawn_quat_wxyz"]).T - off


def hull_eqs(P):
    from scipy.spatial import ConvexHull
    try:
        return ConvexHull(P).equations
    except Exception:  # noqa: BLE001  (flat / degenerate collider)
        return None


def inside_any(X, eqs, tol: float = 1e-4) -> np.ndarray:
    m = np.zeros(len(X), bool)
    for E in eqs:
        if E is not None:
            m |= (X @ E[:, :3].T + E[:, 3] <= tol).all(1)
    return m


def probe(V, F, he_z: float):
    """Cavity of the render mesh: (depth, floor z, r_in) or None when not open."""
    top = he_z + 0.01
    hits = G.ray_hits(np.array([[0.0, 0.0, top]]), np.array([[0.0, 0.0, -1.0]]), V, F)[0]
    if len(hits) == 0:
        return None
    z1 = top - hits[0]
    depth = he_z - z1
    if depth < MIN_DEPTH:
        return None
    zm = z1 + depth / 2
    ang = np.radians(np.arange(0, 360, 45.0))
    D = np.stack([np.cos(ang), np.sin(ang), np.zeros_like(ang)], 1)
    hs = G.ray_hits(np.tile([0.0, 0.0, zm], (8, 1)), D, V, F)
    r = [h[0] for h in hs if len(h)]
    if len(r) < 6:
        return None
    return depth, z1, float(min(r))


def one(k, row, meshes):
    m = np.load(os.path.join(meshes, k + ".npz"))
    V, F = m["v"].astype(float), m["f"].astype(int)
    he = np.asarray(row["half_extents"], float)
    cols = colliders(row["usd_physics"], row.get("body_rel", ""))
    rec = {"id": k, "l9cat": row.get("l9cat"), "n_colliders": len(cols),
           "approx": sorted({c[1] for c in cols}), "height": row.get("height")}
    pr = probe(V, F, float(he[2]))
    if pr is None:
        rec["verdict"] = "not_hollow"
        return rec
    depth, z1, r_in = pr
    eqs = [hull_eqs(to_canonical(c[2], row)) for c in cols]
    zs = z1 + depth * np.array([0.25, 0.5, 0.75])
    ang = np.radians(np.arange(0, 360, 30.0))
    axis = np.stack([np.zeros(3), np.zeros(3), zs], 1)
    ring = lambda r: np.array([[r * math.cos(t), r * math.sin(t), z] for z in zs for t in ang])
    mid = ring(0.5 * r_in)
    wall = ring(max(r_in - WALL_IN, 0.3 * r_in))
    rec.update({"cavity_depth": round(depth, 4), "r_in": round(r_in, 4),
                "filled_axis": round(float(np.r_[inside_any(axis, eqs), inside_any(mid, eqs)].mean()), 3),
                "filled_wall": round(float(inside_any(wall, eqs).mean()), 3)})
    rec["verdict"] = "bad" if rec["filled_wall"] > 0.2 else "ok"
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="/data/harvest/l9v2/rows_mesh.json")
    ap.add_argument("--meshes", default="/data/harvest/l9v2/meshes")
    ap.add_argument("--out", default="/data/harvest/l9v2")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--ids", default="")
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.merge:
        recs = {}
        for f in sorted(glob.glob(os.path.join(a.out, "collider_parts", "collider_*.jsonl"))):
            for line in open(f):
                r = json.loads(line)
                recs[r["id"]] = r
        cnt = {}
        for r in recs.values():
            cnt[r.get("verdict", "err")] = cnt.get(r.get("verdict", "err"), 0) + 1
        with open(os.path.join(a.out, "collider_report.json"), "w") as f:
            json.dump({"rule": __doc__.split("\n\n")[1], "counts": cnt, "objects": recs}, f)
        print(json.dumps(cnt))
        return
    i, n = (int(v) for v in a.shard.split("/"))
    rows = json.load(open(a.rows))
    ids = [s.strip() for s in open(a.ids)] if a.ids else sorted(rows)
    od = os.path.join(a.out, "collider_parts")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, f"collider_{i}.jsonl"), "a") as f:
        for j, k in enumerate(ids):
            if j % n != i or k not in rows or not os.path.exists(os.path.join(a.meshes, k + ".npz")):
                continue
            try:
                rec = one(k, rows[k], a.meshes)
            except Exception as e:  # noqa: BLE001
                rec = {"id": k, "verdict": "err", "err": f"{type(e).__name__}: {e}"}
            f.write(json.dumps(rec) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
