"""L9 v2 diagnosis: vertex bounding box + vertex count of .obj / .stl (ascii or binary) meshes (numpy only).
usage: python tools/l9/diag/mesh_bbox.py <mesh> [<mesh> ...]"""
import struct
import sys

import numpy as np


def load(path: str) -> np.ndarray:
    if path.lower().endswith(".obj"):
        v = [list(map(float, l.split()[1:4])) for l in open(path, errors="ignore") if l.startswith("v ")]
        return np.asarray(v, float)
    raw = open(path, "rb").read()
    if raw[:5] == b"solid" and b"facet" in raw[:400]:
        v = [list(map(float, l.split()[1:4])) for l in raw.decode(errors="ignore").splitlines()
             if l.strip().startswith("vertex")]
        return np.asarray(v, float)
    n = struct.unpack("<I", raw[80:84])[0]
    a = np.frombuffer(raw[84:84 + n * 50], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return a["v"].reshape(-1, 3).astype(float)


def main():
    for p in sys.argv[1:]:
        v = load(p)
        print(p, "n", len(v), "min", np.round(v.min(0), 4).tolist(), "max", np.round(v.max(0), 4).tolist())


if __name__ == "__main__":
    main()
