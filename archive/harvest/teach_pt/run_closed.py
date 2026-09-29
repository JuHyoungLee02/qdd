"""E-PT closed-loop runner (pod, Isaac; one process = one variant + one table height; prereg_pt.md §5):
python -m harvest.teach_pt.run_closed --iface v2|pt|nd-xyz|nd-est|nd-pt --model truth|qwen8b --seeds 0,1
[--variant standard|dr] [--table-z 0.82] [--qwen-url ... --qwen-name ...] --out <dir>
Free models only (truth / local vLLM): paid models are refused here. Same limits as the Astra pilot / proxy / L8
stage 2: prompt limits 40 calls / 180 s, runner early end 20 calls / 60 s; sparse frames on (videos). The world
renders depth only for the pt interface (nd-* and v2 run RGB-only, as at run time).
Output <out>/<iface>_<model>/<variant>[_tz..]/s<seed>/result.json (+ calls/, frames/)."""
from __future__ import annotations

import argparse
import json
import os
import time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--iface", required=True, choices=["v2", "pt", "nd-xyz", "nd-est", "nd-pt"])
    ap.add_argument("--model", required=True, choices=["truth", "qwen8b"])
    ap.add_argument("--arm", default=None, help="output name (default <iface>_<model>)")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--variant", default="standard", choices=["standard", "dr"])
    ap.add_argument("--table-z", type=float, default=None)
    ap.add_argument("--out", default="/data/harvest/out/teach_pt/closed")
    ap.add_argument("--qwen-url", default="http://127.0.0.1:8394")
    ap.add_argument("--qwen-name", default="pt_zs")
    ap.add_argument("--stop-calls", type=int, default=20)
    ap.add_argument("--stop-motion", type=float, default=60.0)
    ap.add_argument("--coords", default="n1000", choices=["n1000", "px"])
    a = ap.parse_args(argv)
    code = 0
    try:
        from ..astra_solo.run import seeds_of
        from ..astra_solo.world import SoloWorld
        from .collect import OOD_H_TABLES
        from .run_collect import variant_dir
        if a.table_z is not None and (a.table_z not in OOD_H_TABLES or a.variant != "standard"):
            raise SystemExit(f"--table-z: one of {OOD_H_TABLES}, variant standard")
        seeds = seeds_of(a.seeds)
        world = SoloWorld(a.variant, depth=a.iface == "pt", table_z=a.table_z)
        print("WORLD " + json.dumps({"table_z": world.table_z, "variant": a.variant, "iface": a.iface}), flush=True)
        model = None
        if a.model == "qwen8b":
            from ..astra_solo.models import LocalVLM
            model = LocalVLM(a.qwen_url, a.qwen_name, "qwen8b")
        arm = a.arm or f"{a.iface}_{a.model}"
        for s in seeds:
            od = os.path.join(a.out, arm, variant_dir(a.variant, a.table_z), f"s{s}")
            if os.path.exists(os.path.join(od, "result.json")):
                continue
            kw = dict(out_dir=od, video=True, variant=a.variant, stop_calls=a.stop_calls, stop_motion_s=a.stop_motion)
            t0 = time.perf_counter()
            if a.iface == "v2":
                from ..astra_solo.episode import Episode
                from ..astra_solo.truth import SoloTruth
                ep = Episode(world, model or SoloTruth(world), s, "mug_tray", **kw)
            else:
                from ..astra_solo.pt_episode import PtEpisode
                from ..astra_solo.pt_truth import NdTruth, PtTruth
                m = model or (PtTruth(world) if a.iface == "pt" else NdTruth(world, a.iface))
                ep = PtEpisode(world, m, s, "mug_tray", iface=a.iface, coords=a.coords, **kw)
                if model is None:
                    m.ep = ep
            res = ep.run()
            print("EP " + json.dumps({k: res.get(k) for k in (
                "seed", "variant", "model", "success", "grasp_lift", "fail_stage", "end_reason", "n_calls",
                "n_invalid", "t_success", "sim_t", "n_clipped", "n_blocked", "interface", "prompt_version")} | {
                "first_close_xy_mm": (res.get("first_close") or {}).get("err_xy_mm"), "table_z": world.table_z,
                "wall_total_s": round(time.perf_counter() - t0, 1)}), flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
