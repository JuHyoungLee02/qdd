"""E-LIBFT checkpoint selection (prereg_libft.md §3): each task's demo_49 first sim state (not trained on, not an
evaluation init state), one closed-loop episode with a served checkpoint on the exact E-LIB0b evaluation path.
usage: select_run.py --suite S --task T --qwen-url U --qwen-name N --arm ARM --out O"""
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
    ap.add_argument("--qwen-url", required=True)
    ap.add_argument("--qwen-name", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default="/data/harvest/lib0/libero_datasets")
    ap.add_argument("--demo", default="demo_49")
    a = ap.parse_args(argv)
    import h5py

    from ..astra_solo import pt_episode as PE
    from ..astra_solo import resolve as RS
    from ..astra_solo.models import LocalVLM
    from ..lib0 import run_a as LA
    from ..teach_pt.run_closed_l8s import ErrCount, claim
    LA.patch_box(True)
    RS.robot_mask = lambda hgt, plane, tcp: np.zeros(np.shape(hgt), bool)
    PE.Monitor = LA.LibMonitor
    from ..lib0.world import GAP_SCALE_B, W_CLOSE_B, LiberoWorld
    world = LiberoWorld(a.suite, a.task)
    world.gap_scale, world.w_close = GAP_SCALE_B, W_CLOSE_B * GAP_SCALE_B
    bddl = os.path.basename(world.bddl).replace(".bddl", "")
    with h5py.File(glob.glob(os.path.join(a.data, a.suite, bddl + "_demo.hdf5"))[0], "r") as f:
        s0 = f["data"][a.demo]["states"][0]
    od = os.path.join(a.out, a.arm, a.suite, f"t{a.task:02d}")
    if not claim(od, f"pid={os.getpid()}"):
        os._exit(0)
    world.init_states = [s0]
    model = ErrCount(LocalVLM(a.qwen_url, a.qwen_name, "q35_libft"))
    t0 = time.perf_counter()
    Ep = LA.episode_class()
    ep = Ep(world, model, 0, "libero", od, video=False, variant="libero", stop_calls=30, stop_motion_s=120.0,
            mem_points=True, fix_loop=True, loop_break=True, stall_n=3, corrupt=None)
    ep.fix_b, ep.fix_c = True, False
    ep.block = LA.lib_block(world)
    res = ep.run()
    row = {"arm": a.arm, "suite": a.suite, "task": a.task, "demo": a.demo, "success": bool(res.get("success")),
           "end_reason": res.get("end_reason"), "n_calls": res.get("n_calls"), "srv_errors": model.errors,
           "wall_s": round(time.perf_counter() - t0, 1)}
    json.dump(row, open(os.path.join(od, "row.json"), "w"))
    print("SEL " + json.dumps(row), flush=True)
    world.close()
    os._exit(0)


if __name__ == "__main__":
    main()
