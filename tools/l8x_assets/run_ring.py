"""Ring-on-peg V episodes (harvest.teach_l8d.xring; pod, Isaac).
usage: python -m tools.l8x_assets.run_ring --rings rings.json --seeds 35480,... --out DIR [--split gate] [--clean]
       [--gaps 0.035] [--video-seeds ...]"""
from __future__ import annotations

import argparse
import os


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rings", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--gaps", default="")
    ap.add_argument("--video-seeds", default="")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.teach_l8d import spec as S
        from harvest.teach_l8d.xring import run_ring
        seeds = [int(s) for s in a.seeds.split(",")]
        for s in seeds:
            S.check_seed(s, a.split)
        gaps = [float(g) for g in a.gaps.split(",") if g.strip()] or None
        run_ring(a.out, a.rings, seeds, a.split, a.clean, gaps=gaps,
                 video={int(v) for v in a.video_seeds.split(",") if v.strip()})
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
