"""boost2 DAgger collection runner (pod, Isaac; one process = one L8-X world config): re-runs L8D b1 TRAIN scenes
(scene.json: variant / table / workspace / lift / seed / task) with the learner (served B-D) driving and the truth
labelling (dagger.DaggerCollector). Output <out>/train/<variant>_tz<z>/<task>_s<seed>/ (labels.jsonl, calls/, meta).
python -m harvest.teach_strip8.run_dagger --qwen-url ... --qwen-name ... --episodes <b1 episode dirs> [--out ...]"""
from __future__ import annotations

import argparse
import json
import os
import time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--qwen-url", required=True)
    ap.add_argument("--qwen-name", required=True)
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--out", default="/data/harvest/out/strip8/dagger")
    a = ap.parse_args(argv)
    code = 0
    try:
        from ..astra_solo.models import LocalVLM
        from ..teach_l8d.run_collect import make_world
        from ..teach_l8d.spec import check_seed
        from ..teach_pt.run_closed_x import config_of
        from .dagger import collect_episode
        cfgs = [config_of(e) for e in a.episodes]
        keys = {(c["variant"], c["table_z"], json.dumps(c["ws"]), c["lift"], c["furniture"]) for c in cfgs}
        if len(keys) != 1 or cfgs[0]["furniture"] is not None:
            raise SystemExit("one non-furniture world config per process")
        c0 = cfgs[0]
        for c in cfgs:
            if c["split"] != "train":
                raise SystemExit("DAgger runs on TRAIN scenes only")
            check_seed(c["seed"], "train")
        world = make_world(c0["variant"], c0["table_z"], c0["ws"], c0["lift"], objset="x")
        print("WORLD " + json.dumps({"table_z": world.table_z, "variant": c0["variant"]}), flush=True)
        model = LocalVLM(a.qwen_url, a.qwen_name, "qwen8b")
        for c in cfgs:
            od = os.path.join(a.out, "train", f"{c['variant']}_tz{c['table_z']:.3f}", f"{c['task']}_s{c['seed']}")
            if os.path.exists(os.path.join(od, "meta.json")):
                continue
            t0 = time.perf_counter()
            meta = collect_episode(world, c["seed"], c["task"], c["variant"], "train", od, model)
            print("EP " + json.dumps(dict(meta, wall_total_s=round(time.perf_counter() - t0, 1))), flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
