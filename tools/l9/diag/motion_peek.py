"""L9 v2 diagnosis: summary of run9_trace motion dumps (pure): step, note, goal vs now, number of world tries, attach,
cuboids near the goal (within 15 cm, world frame).
usage: python tools/l9/diag/motion_peek.py <motion_*.json> ..."""
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from trace_view import qmat  # noqa: E402


def main():
    for f in sys.argv[1:]:
        d = json.load(open(f))
        Tb = np.asarray(d["T_world_base"])
        g, n = np.asarray(d["tcp_T"])[:3, 3], np.asarray(d["tcp_now"])[:3, 3]
        print(f"{f.rsplit('/', 1)[-1]} step={d['step']} note={d['note']} goal {np.round(g, 3).tolist()} now {np.round(n, 3).tolist()} "
              f"tgt {d.get('tgt')} tgt_pos {np.round(d['tgt_pose'][0], 3).tolist() if d.get('tgt_pose') else None}")
        for i, t in enumerate(d.get("tries") or []):
            near = []
            for k, v in t["scene"]["cuboid"].items():
                c = Tb[:3, :3] @ np.asarray(v["pose"][:3]) + Tb[:3, 3]
                if np.linalg.norm(c[:2] - g[:2]) < 0.15:
                    R = Tb[:3, :3] @ qmat(v["pose"][3:])
                    top = c[2] + np.abs(R[2]) @ (np.asarray(v["dims"]) / 2)
                    near.append(f"{k}(top {top:.3f}, d {np.linalg.norm(c[:2] - g[:2]):.3f})")
            print(f"   try {i}: n={len(t['scene']['cuboid'])} attach={t['attach']['names'] if t.get('attach') else None} near goal: {near}")


if __name__ == "__main__":
    main()
