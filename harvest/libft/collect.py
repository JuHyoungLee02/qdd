"""E-LIBFT data collection (prereg_libft.md §2): for each official LIBERO training demo of one task, run the E-LIB0b
evaluation episode path from the demo's first sim state with the demo oracle (harvest.libft.oracle) instead of the
model; every call (prompt, the two images, the oracle answer) is saved exactly as at evaluation time. One process = one
(suite, task) = its demos in order (mkdir claims per demo). Also records, per demo, the held-out check: the largest
absolute difference between the demo's first sim state and each standard init state 0..49 (evaluation uses 0-4).
usage: collect.py --suite S --task T --out O [--demos 0-49]"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import numpy as np


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--task", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default="/data/harvest/lib0/libero_datasets")
    ap.add_argument("--max-demos", type=int, default=50)
    a = ap.parse_args(argv)
    import h5py

    from ..astra_solo import pt_episode as PE
    from ..astra_solo import resolve as RS
    from ..lib0 import run_a as LA
    from ..teach_pt.run_closed_l8s import claim
    from .oracle import DemoPlan, Oracle
    LA.patch_box(True)
    RS.robot_mask = lambda hgt, plane, tcp: np.zeros(np.shape(hgt), bool)
    PE.Monitor = LA.LibMonitor
    from ..lib0.world import GAP_SCALE_B, W_CLOSE_B, LiberoWorld
    world = LiberoWorld(a.suite, a.task)
    world.gap_scale, world.w_close = GAP_SCALE_B, W_CLOSE_B * GAP_SCALE_B
    std_inits = [np.asarray(s) for s in world.init_states]
    bddl = os.path.basename(world.bddl).replace(".bddl", "")
    files = glob.glob(os.path.join(a.data, a.suite, bddl + "_demo.hdf5"))
    if not files:
        raise FileNotFoundError(f"no demo file for {bddl}")
    Ep = LA.episode_class()
    with h5py.File(files[0], "r") as f:
        keys = sorted(f["data"].keys(), key=lambda k: int(k.split("_")[-1]))[: a.max_demos]
        for dk in keys:
            od = os.path.join(a.out, a.suite, f"t{a.task:02d}", dk)
            if not claim(od, f"pid={os.getpid()}"):
                continue
            t0 = time.perf_counter()
            demo = {"actions": f["data"][dk]["actions"][()], "states": f["data"][dk]["states"][()]}
            s0 = demo["states"][0]
            held = [float(np.abs(s0 - s).max()) if s.shape == s0.shape else None for s in std_inits]
            try:
                plan = DemoPlan(world, demo)
                world.init_states = [s0] + std_inits  # reset(0) -> the demo's first state (openpi start: seed 7, 10 waits)
                world.table_z = None
                oracle = Oracle(world, plan, {})
                ep = Ep(world, oracle, 0, "libero", od, video=False, variant="libero", stop_calls=30, stop_motion_s=120.0,
                        mem_points=True, fix_loop=True, loop_break=True, stall_n=3, corrupt=None)
                ep.fix_b, ep.fix_c = True, False
                ep.block = LA.lib_block(world)
                oracle.ep = ep
                res = ep.run()
                world.init_states = std_inits
            except Exception as ex:  # noqa: BLE001
                import traceback
                world.init_states = std_inits
                json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]}, open(os.path.join(od, "error.json"), "w"))
                print("DEMO_ERROR " + json.dumps({"demo": dk, "err": repr(ex)}), flush=True)
                continue
            row = {"suite": a.suite, "task": a.task, "demo": dk, "language": world.task.language,
                   "success": bool(res.get("success")), "end_reason": res.get("end_reason"), "n_calls": res.get("n_calls"),
                   "segments": [s["kind"] for s in plan.segments], "held_min_maxabs": min(h for h in held if h is not None)
                   if any(h is not None for h in held) else None, "held_k0_4": held[:5],
                   "wall_s": round(time.perf_counter() - t0, 1)}
            json.dump(row, open(os.path.join(od, "row.json"), "w"))
            print("DEMO " + json.dumps({k: row[k] for k in ("demo", "success", "end_reason", "n_calls", "segments")}), flush=True)
    world.close()
    print("RUN_DONE", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
