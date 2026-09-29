"""Articulated put-in episodes A / C (harvest.teach_l8d.xart) for one fixture per process (pod, Isaac).
usage: python -m tools.l8x_assets.run_art --kind A|C --fixture NAME --opened opened.json --objects targets.json
       --seeds 49150,49151 --out DIR [--split train|gate] [--clean] [--video-seeds ...]"""
from __future__ import annotations

import argparse
import json
import os


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True)
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--opened", required=True)
    ap.add_argument("--objects", required=True, help="JSON {id: objects_real row} (the L8S target list rows)")
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--video-seeds", default="")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.teach_l8d import spec as S
        from harvest.teach_l8d.xart import run_art
        seeds = [int(s) for s in a.seeds.split(",")]
        for s in seeds:
            S.check_seed(s, a.split)
        run_art(a.out, a.kind, a.fixture, a.opened, a.objects, seeds, a.split, a.clean,
                video={int(v) for v in a.video_seeds.split(",") if v.strip()})
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
