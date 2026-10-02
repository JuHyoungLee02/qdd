"""L9 v2 diagnosis: list the cuboids of a rt9 dump (fail_*.json / scene_*.json) in the planner base frame and in the
world (centre, dims, top / bottom z), nearest first to the base origin, plus the goal / start TCP. Numpy only.
usage: python tools/l9/diag/dump_parts.py <dump.json> [name substring ...]"""
import json
import sys

import numpy as np


def main():
    d = json.load(open(sys.argv[1]))
    keys = sys.argv[2:]
    Tb = np.asarray(d["T_world_base"], float)
    print("base world", np.round(Tb[:3, 3], 3).tolist(), "goal/tcp world", np.round(np.asarray(d["tcp_T"])[:3, 3], 3).tolist())
    rows = []
    for k, v in d["scene"]["cuboid"].items():
        if keys and not any(s in k for s in keys):
            continue
        p = np.asarray(v["pose"][:3], float)
        w = Tb[:3, :3] @ p + Tb[:3, 3]
        dims = np.asarray(v["dims"], float)
        rows.append((float(np.linalg.norm(p[:2])), k, p, w, dims, v["pose"][3:]))
    for r, k, p, w, dims, q in sorted(rows, key=lambda x: x[0]):
        print(f"{k:34s} base {np.round(p, 3).tolist()} world {np.round(w, 3).tolist()} dims {np.round(dims, 3).tolist()} "
              f"z[{w[2] - dims[2] / 2:.3f},{w[2] + dims[2] / 2:.3f}] q {np.round(q, 3).tolist()}")


if __name__ == "__main__":
    main()
