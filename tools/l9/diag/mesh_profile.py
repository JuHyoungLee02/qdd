"""L9 v2 diagnosis: inner-face profile of a finger mesh: for z slices (finger length axis) the minimum of the closing
coordinate (y) over the vertices in that slice (numpy; .obj / .stl).
usage: python tools/l9/diag/mesh_profile.py <mesh> [axis_len=z] [axis_close=y] [n=12]"""
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from mesh_bbox import load  # noqa: E402

AX = {"x": 0, "y": 1, "z": 2}


def main():
    v = load(sys.argv[1])
    al = AX[sys.argv[2]] if len(sys.argv) > 2 else 2
    ac = AX[sys.argv[3]] if len(sys.argv) > 3 else 1
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    lo, hi = v[:, al].min(), v[:, al].max()
    edges = np.linspace(lo, hi, n + 1)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (v[:, al] >= a) & (v[:, al] <= b)
        if m.any():
            print(f"len {a * 1e3:6.1f}..{b * 1e3:6.1f} mm  close-axis min {v[m, ac].min() * 1e3:6.2f} max {v[m, ac].max() * 1e3:6.2f} mm  n {int(m.sum())}")


if __name__ == "__main__":
    main()
