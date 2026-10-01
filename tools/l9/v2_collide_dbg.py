"""L9 v2 diagnosis: which world cuboids put the start state in collision (plain Isaac python + cuRobo pylib).
usage: python tools/l9/v2_collide_dbg.py <scene_*.json from L9V2_DEBUG_DIR> [profile] [arm]"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import curobo9 as C9  # noqa: E402
from harvest.l9 import plan9 as P9  # noqa: E402


def main():
    d = json.load(open(sys.argv[1]))
    prof = sys.argv[2] if len(sys.argv) > 2 else "ffw_sg2"
    arm = sys.argv[3] if len(sys.argv) > 3 else "right"
    pl = P9.Planner9(C9.load_config(prof, arm), self_collision=os.environ.get("SELFCOL", "1") == "1")
    q = np.asarray(d["q"], float)
    Tb = np.asarray(d["T_world_base"], float)
    T = P9.inv_T(Tb) @ np.asarray(d["tcp_T"], float)
    T[2, 3] += 0.02
    print("joints", pl.joint_names, "q", np.round(q, 3).tolist())
    print("base in world", np.round(Tb[:3, 3], 3).tolist())
    lo, hi = pl._limits()
    print("curobo lo", np.round(lo, 3).tolist())
    print("curobo hi", np.round(hi, 3).tolist())
    print("q outside", [(j, round(float(v), 3)) for j, v, a, b in zip(pl.joint_names, q, lo, hi) if v < a or v > b])

    def test(scene, name):
        pl.world(scene)
        Q = pl.pose(q, T)
        ok, _, _ = pl.ik(T[None])
        print(f"{name:40s} plan {'ok' if Q is not None else 'FAIL'}  ik {bool(ok[0])}")
        return Q is not None
    cub = d["scene"]["cuboid"]
    test({"cuboid": {}}, "empty world")
    test(d["scene"], f"full world ({len(cub)} cuboids)")
    for k, v in cub.items():
        if not test({"cuboid": {k: v}}, k):
            print("   ", k, v)


if __name__ == "__main__":
    main()
