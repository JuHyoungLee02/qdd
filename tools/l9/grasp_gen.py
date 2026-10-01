"""L9 v2: analytic grasp candidates for every exported mesh (harvest/l9/grasp9.py), one gripper, CPU shard.
  python tools/l9/grasp_gen.py --meshes /data/harvest/l9v2/meshes --grip ffw_sg2 --out /data/harvest/l9v2/grasps --shard i/n
Writes <out>/<grip>/<id>.npz (T, c1, c2, w, a, score, pre_open) and a log line per object (count per family)."""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import grasp9 as G  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meshes", required=True)
    ap.add_argument("--grip", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--n-surface", type=int, default=3000)
    a = ap.parse_args()
    i, n = (int(v) for v in a.shard.split("/"))
    od = os.path.join(a.out, a.grip)
    os.makedirs(od, exist_ok=True)
    log = open(os.path.join(od, f"_log_{i}.jsonl"), "a")
    files = sorted(glob.glob(os.path.join(a.meshes, "*.npz")))
    for j, f in enumerate(files):
        k = os.path.basename(f)[:-4]
        dst = os.path.join(od, k + ".npz")
        if j % n != i or os.path.exists(dst):
            continue
        t0 = time.time()
        try:
            m = np.load(f)
            C = G.sample_grasps(m["v"], m["f"], a.grip, seed=j, n_surface=a.n_surface)
            np.savez_compressed(dst, **{x: C[x] for x in ("T", "c1", "c2", "w", "a", "score", "pre_open")})
            fam = [G.family_obj(v) for v in C["a"]]
            log.write(json.dumps({"id": k, "n": int(len(C["w"])), "top": fam.count("top"),
                                  "oblique": fam.count("oblique"), "horizontal": fam.count("horizontal"),
                                  "w_min": float(C["w"].min()) if len(C["w"]) else None,
                                  "s": round(time.time() - t0, 1)}) + "\n")
        except Exception as e:
            log.write(json.dumps({"id": k, "err": f"{type(e).__name__}: {e}"}) + "\n")
        log.flush()


if __name__ == "__main__":
    main()
