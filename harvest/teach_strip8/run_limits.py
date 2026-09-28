"""user-log 171 closed-loop runner (prereg_limits.md; one Isaac process = one L8-X world config): each condition runs
every given episode with the boost1b executor (point-cloud memory + 'above' switch) and optional corruption / rescue.
--conds none,hole:0.3,hole:0.3:r,noise:2,light:dim_warm,occl:0.6  (':r' = depth rescue on)
python -m harvest.teach_strip8.run_limits --conds ... --qwen-url ... --qwen-name ... --out <dir> --episodes <dirs>
Output <out>/<arm>/<split>/<variant>_tz<z>/s<seed>_<task>/result.json, arm = cond with ':' -> '_'."""
from __future__ import annotations

import argparse
import json
import os
import time


def parse(cond: str):
    """-> (corrupt | None, rescue, resolver). Extras after the level: 'r' = rescue, 'v2' = resolver v2."""
    p = cond.split(":")
    if p[0] == "none":
        ex = p[1:]
        return None, "r" in ex, "v2" if "v2" in ex else "v1"
    lv = p[1] if p[0] == "light" else float(p[1])
    ex = p[2:]
    return (p[0], lv), "r" in ex, "v2" if "v2" in ex else "v1"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--conds", required=True)
    ap.add_argument("--qwen-url", required=True)
    ap.add_argument("--qwen-name", required=True)
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--out", required=True)
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
        from .boost import LimitEpisode
        cfgs = [config_of(e) for e in a.episodes]
        keys = {(c["variant"], c["table_z"], json.dumps(c["ws"]), c["lift"], c["furniture"]) for c in cfgs}
        if len(keys) != 1 or cfgs[0]["furniture"] is not None:
            raise SystemExit("one non-furniture world config per process")
        c0 = cfgs[0]
        for c in cfgs:
            check_seed(c["seed"], c["split"], True)
        world = make_world(c0["variant"], c0["table_z"], c0["ws"], c0["lift"], objset="x")
        print("WORLD " + json.dumps({"table_z": world.table_z, "conds": a.conds}), flush=True)
        model = LocalVLM(a.qwen_url, a.qwen_name, "qwen8b")
        for cond in a.conds.split(","):
            corrupt, rescue, resolver = parse(cond)
            arm = cond.replace(":", "_")
            for c in cfgs:
                if c["task"] in X_STEPS:
                    continue
                od = os.path.join(a.out, arm, c["split"], f"{c['variant']}_tz{c['table_z']:.3f}",
                                  f"s{c['seed']}_{c['task']}")
                if os.path.exists(os.path.join(od, "result.json")):
                    continue
                t0 = time.perf_counter()
                ep = LimitEpisode(world, model, c["seed"], c["task"], od, video=True, variant=c["variant"],
                                  stop_calls=a.stop_calls, stop_motion_s=a.stop_motion, mem_points=True, fix_loop=True,
                                  corrupt=corrupt, rescue=rescue, resolver=resolver)
                res = ep.run()
                print("EP " + json.dumps({k: res.get(k) for k in (
                    "seed", "task", "success", "grasp_lift", "fail_stage", "end_reason", "n_calls")} | {
                    "arm": arm, "limits": res.get("limits"), "wall_total_s": round(time.perf_counter() - t0, 1)}),
                    flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
