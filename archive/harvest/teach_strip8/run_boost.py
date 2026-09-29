"""boost1 closed loop (prereg_boost1.md; pod, Isaac; one process = one L8-X world config): the E-DIST8 run_closed_x
episodes with BoostEpisode (d-min, B-D model) and the fixes off ('before') or on ('after').
python -m harvest.teach_strip8.run_boost --fix off|on --qwen-url ... --qwen-name ... --arm <name> --episodes <dirs>
Limits = E-PT / E-DIST8: prompt 40 calls / 180 s, early end 20 / 60 s. Free models only."""
from __future__ import annotations

import argparse
import json
import os
import time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", choices=["off", "on"], help="boost1: both fixes off / on (one arm = --arm)")
    ap.add_argument("--combos", default="", help="boost1b: mem:perturb,... mem none|img|pts (loop fix on), perturb none|tray|lift|head; arm = <mem>_<perturb>")
    ap.add_argument("--qwen-url", required=True)
    ap.add_argument("--qwen-name", required=True)
    ap.add_argument("--arm", default="")
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--out", default="/data/harvest/out/strip8/boost1")
    ap.add_argument("--stop-calls", type=int, default=20)
    ap.add_argument("--stop-motion", type=float, default=60.0)
    a = ap.parse_args(argv)
    code = 0
    try:
        from ..astra_solo.models import LocalVLM
        from ..sim.tasks import X_STEPS
        from ..teach_l8d.run_collect import make_world
        from ..teach_l8d.spec import check_seed
        from ..teach_pt.run_closed_x import config_of
        from .boost import PerturbEpisode
        cfgs = [config_of(e) for e in a.episodes]
        keys = {(c["variant"], c["table_z"], json.dumps(c["ws"]), c["lift"], c["furniture"]) for c in cfgs}
        if len(keys) != 1 or cfgs[0]["furniture"] is not None:
            raise SystemExit("one non-furniture world config per process")
        c0 = cfgs[0]
        for c in cfgs:
            check_seed(c["seed"], c["split"], True)
        world = make_world(c0["variant"], c0["table_z"], c0["ws"], c0["lift"], objset="x")
        print("WORLD " + json.dumps({"table_z": world.table_z, "fix": a.fix, "combos": a.combos}), flush=True)
        model = LocalVLM(a.qwen_url, a.qwen_name, "qwen8b")
        if a.combos:
            combos = [(x.split(":") + [""])[:3] for x in a.combos.split(",")]  # mem:perturb[:extras a/d]
            runs = [(f"{m}_{p}" + (f"_{e}" if e else ""),
                     dict(fix_mem=m == "img", mem_points=m == "pts", fix_loop=True, perturb=None if p == "none" else p,
                          recheck="a" in e, fix_descend="d" in e)) for m, p, e in combos]
        else:
            on = a.fix == "on"
            runs = [(a.arm, dict(fix_mem=on, fix_loop=on, perturb=None))]
        for arm, kw in runs:
            for c in cfgs:
                if c["task"] in X_STEPS:
                    continue
                od = os.path.join(a.out, arm, c["split"], f"{c['variant']}_tz{c['table_z']:.3f}",
                                  f"s{c['seed']}_{c['task']}")
                if os.path.exists(os.path.join(od, "result.json")):
                    continue
                t0 = time.perf_counter()
                ep = PerturbEpisode(world, model, c["seed"], c["task"], od, video=True, variant=c["variant"],
                                    stop_calls=a.stop_calls, stop_motion_s=a.stop_motion, **kw)
                res = ep.run()
                print("EP " + json.dumps({k: res.get(k) for k in (
                    "seed", "task", "success", "grasp_lift", "fail_stage", "end_reason", "n_calls", "t_success")} | {
                    "arm": arm, "boost": res.get("boost"), "table_z": world.table_z,
                    "wall_total_s": round(time.perf_counter() - t0, 1)}), flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
