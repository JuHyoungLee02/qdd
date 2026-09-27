"""E-DIST8 closed loop on L8-X evaluation scenes (prereg_dist8.md §5; pod, Isaac; one process = one world config).
Re-runs chosen L8D OOD episodes (same split / variant / table height / workspace box / lift / seed / task, from each
episode's scene.json) with a local vLLM model through an E-DIST8 interface (r-min / d-min / h-min), world built by
harvest.teach_l8d.run_collect.make_world (objset x, depth on). Only single-step, non-furniture tasks. Free models only.
python -m harvest.teach_pt.run_closed_x --iface d-min --qwen-url http://127.0.0.1:8440 --qwen-name d8_b_d_min
  --arm b_d-min --episodes <L8D episode dir> [...] [--h-depth on|noisy|off] --out /data/harvest/out/dist8/closed
All episodes given must share one world config (checked). Limits = E-PT: prompt 40 calls / 180 s, early end 20 / 60 s."""
from __future__ import annotations

import argparse
import json
import os
import time


def config_of(ep_dir: str) -> dict:
    s = json.load(open(os.path.join(ep_dir, "scene.json")))
    return {"variant": s["variant"], "table_z": float(s["table_z"]), "ws": tuple(tuple(map(float, v)) for v in s["ws"]),
            "lift": s.get("lift"), "task": s["task"], "seed": int(s["seed"]), "split": s["split"],
            "furniture": s.get("furniture")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--iface", required=True, choices=["r-min", "d-min", "h-min"])
    ap.add_argument("--h-depth", default="on", choices=["on", "noisy", "off"])
    ap.add_argument("--qwen-url", required=True)
    ap.add_argument("--qwen-name", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--out", default="/data/harvest/out/dist8/closed")
    ap.add_argument("--confirm-ood", action="store_true", help="evaluation on protected OOD seeds (never trained)")
    ap.add_argument("--stop-calls", type=int, default=20)
    ap.add_argument("--stop-motion", type=float, default=60.0)
    a = ap.parse_args(argv)
    code = 0
    try:
        cfgs = [config_of(e) for e in a.episodes]
        keys = {(c["variant"], c["table_z"], json.dumps(c["ws"]), c["lift"], c["furniture"]) for c in cfgs}
        if len(keys) != 1:
            raise SystemExit(f"episodes span {len(keys)} world configs; one process = one config")
        c0 = cfgs[0]
        if c0["furniture"] is not None:
            raise SystemExit("furniture scenes are not supported here")
        from ..astra_solo.models import LocalVLM
        from ..astra_solo.pt_episode import PtEpisode
        from ..sim.tasks import X_STEPS
        from ..teach_l8d.run_collect import make_world
        from ..teach_l8d.spec import check_seed
        for c in cfgs:
            check_seed(c["seed"], c["split"], a.confirm_ood)
        world = make_world(c0["variant"], c0["table_z"], c0["ws"], c0["lift"], objset="x")
        print("WORLD " + json.dumps({"table_z": world.table_z, **{k: c0[k] for k in ("variant", "ws", "lift")}}), flush=True)
        model = LocalVLM(a.qwen_url, a.qwen_name, "qwen8b")
        for c in cfgs:
            if c["task"] in X_STEPS:
                print("SKIP " + json.dumps({"seed": c["seed"], "task": c["task"], "why": "multi-step"}), flush=True)
                continue
            tag = a.arm + ("" if a.iface != "h-min" else f"_{a.h_depth}")
            od = os.path.join(a.out, tag, c["split"], f"{c['variant']}_tz{c['table_z']:.3f}", f"s{c['seed']}_{c['task']}")
            if os.path.exists(os.path.join(od, "result.json")):
                continue
            t0 = time.perf_counter()
            ep = PtEpisode(world, model, c["seed"], c["task"], od, iface=a.iface, h_depth=a.h_depth, video=True,
                           variant=c["variant"], stop_calls=a.stop_calls, stop_motion_s=a.stop_motion)
            res = ep.run()
            print("EP " + json.dumps({k: res.get(k) for k in (
                "seed", "task", "variant", "success", "grasp_lift", "fail_stage", "end_reason", "n_calls", "n_invalid",
                "t_success", "sim_t", "interface", "fallback_rate")} | {
                "table_z": world.table_z, "first_close_xy_mm": (res.get("first_close") or {}).get("err_xy_mm"),
                "wall_total_s": round(time.perf_counter() - t0, 1)}), flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
