"""E-PT collection runner (pod, Isaac, one process = one variant and one table height; = teach_l8.run_collect with a
depth-rendering world and the pt episode). python -m harvest.teach_pt.run_collect --split train|dev|ood_d|ood_h
--variant standard|dr|random --seeds 20100-20249 [--table-z 0.82] [--out ...].
Output <out>/<split>/<variant>[_tz<table z>]/<task>_s<seed>/; finished episodes are skipped (resume)."""
from __future__ import annotations

import argparse
import json
import os
import time

OUT = "/data/harvest/out/teach_pt/collect"


def make_world(variant: str, table_z=None):
    from ..astra_motion.world_isaac import IsaacWorld
    from ..astra_solo.world import SoloWorld

    class PtL8World(SoloWorld):
        """SoloWorld with depth and the R2 tasks (TRAIN); DEV / ood_d / ood_h stay mug_tray."""

        def reset(self, seed, task="mug_tray"):
            IsaacWorld.reset(self, seed, task)

    return PtL8World(variant, depth=True, table_z=table_z)


def variant_dir(variant: str, table_z) -> str:
    return variant if table_z is None else f"{variant}_tz{float(table_z):.2f}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev", "ood_d", "ood_h"], required=True)
    ap.add_argument("--variant", choices=["standard", "dr", "random"], required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--table-z", type=float, default=None)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--p", type=float, default=0.35)
    ap.add_argument("--max-perturb", type=int, default=4)
    ap.add_argument("--clean-share", type=float, default=0.25)
    ap.add_argument("--stop-calls", type=int, default=30)
    ap.add_argument("--stop-motion", type=float, default=120.0)
    a = ap.parse_args(argv)
    code = 0
    try:
        from ..teach_l8.run_collect import parse_seeds, style_of
        from .collect import check_seed, collect_episode, task_of
        seeds = [check_seed(s, a.split, a.variant, a.table_z) for s in parse_seeds(a.seeds)]
        world = make_world(a.variant, a.table_z)
        print("WORLD " + json.dumps({"table_z": world.table_z, "variant": a.variant}), flush=True)
        for s in seeds:
            task = task_of(s, a.split)
            od = os.path.join(a.out, a.split, variant_dir(a.variant, a.table_z), f"{task}_s{s}")
            if os.path.exists(os.path.join(od, "meta.json")):
                continue
            style = style_of(s, a.clean_share)
            t0 = time.perf_counter()
            meta = collect_episode(world, s, task, a.variant, od, 0.0 if style == "clean" else a.p, a.max_perturb,
                                   a.stop_calls, a.stop_motion, style)
            print("EP " + json.dumps(dict(meta, wall_total_s=round(time.perf_counter() - t0, 1))), flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
