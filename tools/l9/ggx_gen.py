"""L9 v2: GraspGenX candidates for every exported mesh, one gripper, written next to the analytic cache's format
(harvest/l9/ggx_cache.py does the conversion; the sim test is tools/l9/grasp_test.py --grasps <this out>).
  GGX_QUEUE=<queue> python tools/l9/ggx_gen.py --meshes /data/harvest/l9v2/meshes --grip ffw_sg2 \
      --out /data/harvest/l9v2/grasps_ggx --shard i/n [--ids file]
Writes <out>/<grip>/<id>.npz (T, c1, c2, w, a, score, pre_open; score = GGX confidence) + one GGXDBG log line per
object (requested / returned / seated counts, families)."""
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
from harvest.l9 import ggx_cache as GC  # noqa: E402
from harvest.l9.ggx_refine import _tcp_in_base  # noqa: E402
from tools.l9.graspgenx_client import base_to_tcp, request_grasps  # noqa: E402


# served gripper name per cache gripper: AIW = the verified converter asset (base_link + tcp_in_base); Franka = a
# TCP-frame sweep volume (frame G as the GGX base, tools/l9/g1_ggx_sweep.sweep on franka_hand.json, gripper_type 0):
# the base_link converter gave poses scattered around the object (pod probe 10-03), the curated franka_panda path
# of the shared server is broken (GraspGenXSampler.from_gripper_name missing)
GGX_NAME = {"ffw_sg2": "ffw_sg2_right", "franka": "franka_hand_tcp"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meshes", required=True)
    ap.add_argument("--grip", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--ids", default=None, help="optional: only these object ids (one per line), in this order")
    ap.add_argument("--n-points", type=int, default=2048)
    ap.add_argument("--num-grasps", type=int, default=200)
    ap.add_argument("--timeout", type=float, default=120.0)
    a = ap.parse_args()
    i, n = (int(v) for v in a.shard.split("/"))
    od = os.path.join(a.out, a.grip)
    os.makedirs(od, exist_ok=True)
    log = open(os.path.join(od, f"_log_{i}.jsonl"), "a")
    name = GGX_NAME.get(a.grip, G.JSON_NAME.get(a.grip, a.grip))
    xyz, rpy = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)) if name.endswith("_tcp") else _tcp_in_base(name)
    if a.ids:
        files = [os.path.join(a.meshes, s.strip() + ".npz") for s in open(a.ids) if s.strip()]
    else:
        files = sorted(glob.glob(os.path.join(a.meshes, "*.npz")))
    for j, f in enumerate(files):
        k = os.path.basename(f)[:-4]
        dst = os.path.join(od, k + ".npz")
        if j % n != i or os.path.exists(dst) or not os.path.exists(f):
            continue
        t0 = time.time()
        try:
            m = np.load(f)
            V, F = np.asarray(m["v"], float), np.asarray(m["f"], int)
            P, _, _ = G.sample_surface(V, F, a.n_points, np.random.default_rng(j))
            centre = P.mean(0)
            gr, sc, status = request_grasps((P - centre).astype(np.float32), gripper=name,
                                            num_grasps=a.num_grasps, timeout_s=a.timeout)
            if status != "ok":
                print(f"GGXDBG gen {a.grip} {k} status={status[:200]}", flush=True)
                log.write(json.dumps({"id": k, "err": status[:300]}) + "\n")
                log.flush()
                continue
            poses = []
            for Tg in gr:
                R, t = base_to_tcp(np.asarray(Tg[:3, :3], float), np.asarray(Tg[:3, 3], float), xyz, rpy)
                poses.append((R, t + centre))
            why = {}
            C = GC.candidates(V, F, a.grip, poses, sc, seed=j, why=why)
            np.savez_compressed(dst, **C)
            fam = [G.family_obj(v) for v in C["a"]]
            rec = {"id": k, "req": a.num_grasps, "ret": int(len(gr)), "n": int(len(C["w"])), "top": fam.count("top"),
                   "oblique": fam.count("oblique"), "horizontal": fam.count("horizontal"),
                   "conf_max": round(float(sc.max()), 3) if len(sc) else None, "why": why, "s": round(time.time() - t0, 1)}
            print("GGXDBG gen", a.grip, json.dumps(rec), flush=True)
            log.write(json.dumps(rec) + "\n")
        except Exception as e:
            log.write(json.dumps({"id": k, "err": f"{type(e).__name__}: {e}"}) + "\n")
        log.flush()


if __name__ == "__main__":
    main()
