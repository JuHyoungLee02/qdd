"""E-STRIP8 closed-loop runner (pod, Isaac; one process = one variant + one table height; prereg_strip8.md §5.3):
python -m harvest.teach_strip8.run_closed --iface s-min|v2 --model truth|qwen8b --seeds 0,1 [--variant standard|dr]
[--table-z 0.82] [--qwen-url ... --qwen-name ...] --arm <name> --out <dir>
Free models only (truth / local vLLM). Same limits as E-TEACH-L8 stage 2 / E-PT: prompt limits 40 calls / 180 s,
runner early end 20 calls / 60 s; sparse frames on (videos). RGB only (no depth).
Output <out>/<arm>/<variant>[_tz..]/s<seed>/result.json (+ calls/, frames/)."""
from __future__ import annotations

import argparse
import json
import os
import time

IFACES = ("s-min", "v2")


def make_episode(iface: str, world, model, seed: int, **kw):
    if iface == "s-min":
        from ..astra_solo.pt_truth import NdTruth
        from .episode import StripEpisode
        m = model or NdTruth(world, "nd-xyz")
        ep = StripEpisode(world, m, seed, "mug_tray", **kw)
    elif iface == "v2":
        from ..astra_solo.episode import Episode
        from ..astra_solo.truth import SoloTruth
        m = model or SoloTruth(world)
        ep = Episode(world, m, seed, "mug_tray", **kw)
    else:
        raise ValueError(f"iface {iface}: one of {IFACES}")
    if model is None and hasattr(m, "ep"):
        m.ep = ep
    return ep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--iface", required=True, choices=IFACES)
    ap.add_argument("--model", required=True, choices=["truth", "qwen8b"])
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--variant", default="standard", choices=["standard", "dr"])
    ap.add_argument("--table-z", type=float, default=None)
    ap.add_argument("--out", default="/data/harvest/out/strip8/closed")
    ap.add_argument("--qwen-url", default="http://127.0.0.1:8396")
    ap.add_argument("--qwen-name", default="s8")
    ap.add_argument("--stop-calls", type=int, default=20)
    ap.add_argument("--stop-motion", type=float, default=60.0)
    a = ap.parse_args(argv)
    code = 0
    try:
        from ..astra_solo.run import seeds_of
        from ..astra_solo.world import SoloWorld
        from ..teach_pt.collect import OOD_H_TABLES
        from ..teach_pt.run_collect import variant_dir
        if a.table_z is not None and (a.table_z not in OOD_H_TABLES or a.variant != "standard"):
            raise SystemExit(f"--table-z: one of {OOD_H_TABLES}, variant standard")
        world = SoloWorld(a.variant, depth=False, table_z=a.table_z)
        print("WORLD " + json.dumps({"table_z": world.table_z, "variant": a.variant, "iface": a.iface}), flush=True)
        model = None
        if a.model == "qwen8b":
            from ..astra_solo.models import LocalVLM
            model = LocalVLM(a.qwen_url, a.qwen_name, "qwen8b")
        for s in seeds_of(a.seeds):
            od = os.path.join(a.out, a.arm, variant_dir(a.variant, a.table_z), f"s{s}")
            if os.path.exists(os.path.join(od, "result.json")):
                continue
            t0 = time.perf_counter()
            ep = make_episode(a.iface, world, model, s, out_dir=od, video=True, variant=a.variant,
                              stop_calls=a.stop_calls, stop_motion_s=a.stop_motion)
            res = ep.run()
            print("EP " + json.dumps({k: res.get(k) for k in (
                "seed", "variant", "model", "success", "grasp_lift", "fail_stage", "end_reason", "n_calls",
                "n_invalid", "t_success", "sim_t", "n_clipped", "n_blocked", "interface", "prompt_version")} | {
                "first_close_xy_mm": (res.get("first_close") or {}).get("err_xy_mm"), "table_z": world.table_z,
                "arm": a.arm, "wall_total_s": round(time.perf_counter() - t0, 1)}), flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
