"""L9 v2: export object meshes in the canonical frame (harvest/sim/objv.py: bbox centre of the upright object,
identity quaternion when upright) for the pure grasp sampler (harvest/l9/grasp9.py).

Run with the Isaac python (pxr), no SimulationApp needed:
  /isaac-sim/python.sh tools/l9/mesh_export.py --ids ids.txt --out /data/harvest/l9v2/meshes [--shard i/n]
Per object: <out>/<id>.npz with v (N,3) float32 canonical metres, f (M,3) int32, plus a check line
(canonical bbox vs catalog half_extents) in <out>/_log_<shard>.jsonl.

Frame math (objv.canonical_from_root): world x = root + R(q_root) p_root, q_root = qc * spawn, c = root + R(qc) off
  => p_can = R(spawn) p_root - off,  off = (cx, cy, height/2 - root_above_bottom).
p_root = the point relative to the rigid-body prim (body_rel) without scale (physics poses carry no scale)."""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np


def qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def mesh_of(usd_path: str, body_rel: str):
    from pxr import Usd, UsdGeom
    st = Usd.Stage.Open(usd_path)
    dp = st.GetDefaultPrim()
    cache = UsdGeom.XformCache()
    body = st.GetPrimAtPath(dp.GetPath().AppendPath(body_rel)) if body_rel else dp
    if not body or not body.IsValid():
        body = dp
    Mb = np.array(cache.GetLocalToWorldTransform(body), float).T  # USD row-vector matrices -> column form
    Rb = Mb[:3, :3]
    U, _, Vt = np.linalg.svd(Rb)
    Rb = U @ Vt  # rotation only (drop scale)
    tb = Mb[:3, 3]
    V, F, off = [], [], 0
    for p in Usd.PrimRange(dp):
        if not p.IsA(UsdGeom.Mesh):
            continue
        if UsdGeom.Imageable(p).ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        m = UsdGeom.Mesh(p)
        pts = m.GetPointsAttr().Get()
        cnt = m.GetFaceVertexCountsAttr().Get()
        idx = m.GetFaceVertexIndicesAttr().Get()
        if pts is None or cnt is None or idx is None or len(pts) == 0:
            continue
        M = np.array(cache.GetLocalToWorldTransform(p), float).T
        P = np.asarray(pts, float)
        Pw = P @ M[:3, :3].T + M[:3, 3]
        V.append(Pw)
        cnt, idx = np.asarray(cnt, int), np.asarray(idx, int)
        k = 0
        tris = []
        for c in cnt:  # fan triangulation
            for j in range(1, c - 1):
                tris.append((idx[k], idx[k + j], idx[k + j + 1]))
            k += c
        F.append(np.asarray(tris, int) + off)
        off += len(P)
    if not V:
        return None, None
    Vw = np.concatenate(V)
    Vb = (Vw - tb) @ Rb  # = Rb^T (x - tb)
    return Vb, np.concatenate(F)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True, help="json {id: catalog row} (usd_physics, body_rel, spawn_quat_wxyz, ...)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args()
    i, n = (int(v) for v in a.shard.split("/"))
    rows = json.load(open(a.rows))
    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, f"_log_{i}.jsonl"), "a")
    for j, (k, r) in enumerate(sorted(rows.items())):
        if j % n != i or os.path.exists(os.path.join(a.out, k + ".npz")):
            continue
        try:
            Vb, F = mesh_of(r["usd_physics"], r.get("body_rel", ""))
            if Vb is None:
                log.write(json.dumps({"id": k, "err": "no mesh"}) + "\n")
                continue
            cx, cy = r.get("centre_from_root_xy", (0.0, 0.0))
            off = np.array([cx, cy, float(r["height"]) / 2 - float(r["root_above_bottom"])])
            Vc = Vb @ qmat(r["spawn_quat_wxyz"]).T - off
            lo, hi = Vc.min(0), Vc.max(0)
            np.savez_compressed(os.path.join(a.out, k + ".npz"), v=Vc.astype(np.float32), f=F.astype(np.int32))
            he = np.asarray(r["half_extents"], float)
            log.write(json.dumps({"id": k, "nv": int(len(Vc)), "nf": int(len(F)), "lo": lo.round(4).tolist(),
                                  "hi": hi.round(4).tolist(), "he": he.round(4).tolist(),
                                  "err_mm": float(np.abs(np.concatenate([hi - he, -lo - he])).max() * 1000)}) + "\n")
        except Exception as e:  # keep going; the log says which failed
            log.write(json.dumps({"id": k, "err": f"{type(e).__name__}: {e}"}) + "\n")
        log.flush()
    print("done", i, n, file=sys.stderr)


if __name__ == "__main__":
    main()
