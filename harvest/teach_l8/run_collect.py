"""E-TEACH-L8 collection runner (pod, Isaac; one process = one scene variant):
python -m harvest.teach_l8.run_collect --split train|dev --variant standard|dr --seeds 20000-20039 [--out ...]
Episode style per seed: 'clean' (p = 0) with probability --clean-share, else 'mixed' (p = --p, at most --max-perturb
perturbations). Output <out>/<split>/<variant>/<task>_s<seed>/ (calls/, result.json, labels.jsonl, meta.json);
finished episodes (meta.json present) are skipped (resume)."""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

OUT = "/data/harvest/out/teach_l8/collect"


def parse_seeds(spec: str) -> list:
    out = []
    for part in spec.split(","):
        a, _, b = part.strip().partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def style_of(seed: int, clean_share: float) -> str:
    return "clean" if np.random.default_rng([int(seed), 8, 77]).random() < clean_share else "mixed"


def make_world(variant: str):
    from ..astra_motion.world_isaac import IsaacWorld
    from ..astra_solo.world import SoloWorld

    class L8World(SoloWorld):
        """SoloWorld with the R2 tasks mug_tray / bottle_tray / mug_marker (TRAIN); DEV stays mug_tray."""

        def reset(self, seed, task="mug_tray"):
            IsaacWorld.reset(self, seed, task)

    return L8World(variant)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "dev"], required=True)
    ap.add_argument("--variant", choices=["standard", "dr"], required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--p", type=float, default=0.35)
    ap.add_argument("--max-perturb", type=int, default=4)
    ap.add_argument("--clean-share", type=float, default=0.25)
    ap.add_argument("--stop-calls", type=int, default=30)
    ap.add_argument("--stop-motion", type=float, default=120.0)
    a = ap.parse_args(argv)
    code = 0
    try:
        from .collect import check_seed, collect_episode, task_of
        seeds = [check_seed(s, a.split) for s in parse_seeds(a.seeds)]
        world = make_world(a.variant)
        for s in seeds:
            task = task_of(s, a.split)
            od = os.path.join(a.out, a.split, a.variant, f"{task}_s{s}")
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
    os._exit(code)  # SimulationApp.close() hangs in this chroot (astra_solo.run)


if __name__ == "__main__":
    main()
