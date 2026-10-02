"""L9 bimanual category-A (handover) smoke (pod, Isaac): draws one scene + one target object through the existing
task9/scene9/pool path (so the object has a cached grasp candidate file -- a pod check confirmed candidate caches
are keyed by pool catalog id, not by the demo/X_RIGID object ids), builds a dual SimEnv, and runs
`harvest.l9.bimanual9.HandoverRuntime.run_episode` end to end. Saves head + both wrist PNGs and a result.json per
episode; NOT the production collection loop (harvest/l9/bimanual9.py spec note §3 / docs/superpowers/specs/
2026-10-02-l9-bimanual.md).

usage: python -m tools.l9.bim_smoke --out DIR [--n 2] [--seed0 3950000] [--robot ffw_sg2] [--direction rl]
       [--cat block] [--pool 5000] [--rooms 5000] [--gpu0 for device selection via CUDA_VISIBLE_DEVICES already set]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _jsonable(o):
    import numpy as np
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return str(o)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=3950000)
    ap.add_argument("--robot", default="ffw_sg2")
    ap.add_argument("--direction", default="rl", choices=["rl", "lr"])  # rl: giver=right (env primary), receiver=left
    ap.add_argument("--cat", default="block", choices=list("block can cup bottle bowl box".split()))
    ap.add_argument("--pool", type=int, default=5000)
    ap.add_argument("--rooms", type=int, default=5000)
    ap.add_argument("--device", default="cuda:0")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    results = []
    try:
        import numpy as np

        from harvest.l9 import assets9 as A9
        from harvest.l9 import bimanual9 as B
        from harvest.l9 import reach9 as R9
        from harvest.l9 import rt9 as RT
        from harvest.l9 import scene9 as S9
        from harvest.l9 import task9 as T9
        from harvest.l9 import vary9 as V
        from harvest.l9.world9 import make_world9
        from harvest.l9.run9 import rooms_for

        giver, receiver = ("right", "left") if a.direction == "rl" else ("left", "right")
        cats = B.BIM_A_OBJECTS[a.cat]
        pool = A9.pool_for(a.pool, "train")
        pool = {k: v for k, v in pool.items() if v.get("role9") != "target" or RT.has_candidates(a.robot, k, True)}
        n_targets = sum(1 for v in pool.values() if v.get("role9") == "target")
        print("POOL " + json.dumps({"size": len(pool), "targets_with_candidates": n_targets}), flush=True)
        rooms = rooms_for(a.rooms, "train")
        mesh = A9.mesh_for(a.rooms, split="train")
        rm = R9.load_default()
        family, rule = S9.all_rules("train")[0]
        world = make_world9(giver, pool, rooms, mesh=mesh, robot=a.robot, dual=True)
        print("WORLD " + json.dumps({"arm": world.arm, "pool": len(pool), "dual": world.env.dual,
                                     "primary": world.env.primary}), flush=True)
        defn = T9.TaskDef("bim_a_smoke_" + a.cat, "bim_a", {"A": {"role": "target", "cats": cats}},
                          {"P": {"type": "spot", "corner": "centre"}}, (("A", "P"),), ("Pick the {A}.",) * 5)
        for i in range(a.n):
            seed = a.seed0 + i
            t0 = time.time()
            ep, sc = None, None
            for k in range(20):
                sd = seed + 100003 * k
                try:
                    sc = S9.sample(family, rule, sd, giver, rm)
                except RuntimeError:
                    continue
                ep = T9.instantiate(defn, sc, pool, sd, rm, grip_max=world.w_open)
                if ep is not None:
                    break
            if ep is None:
                results.append({"seed": seed, "ok": False, "status": "no scene / object draw"})
                continue
            light, head = V.pick_light_family(sd, "bim_a"), V.head_pose(sd)
            world.prepare(sc, ep, light, head, sd)
            obj_key = ep["steps"][0][0]
            print("DRAW " + json.dumps({"seed": seed, "obj": obj_key, "wall_s": round(time.time() - t0, 1)}),
                  flush=True)
            hr = B.install_handover(world, a.robot, giver, receiver, device=a.device, allow_untested=True)
            r = hr.run_episode(obj_key, world.table_z)
            r["seed"], r["obj"] = seed, obj_key
            r["wall_s"] = round(time.time() - t0, 1)
            print("EP " + json.dumps({k: v for k, v in r.items() if k != "log"}, default=_jsonable), flush=True)
            results.append(r)
            try:
                from PIL import Image
                od = os.path.join(a.out, f"ep{i}")
                os.makedirs(od, exist_ok=True)
                for cam, name in (("cam_head", "head"), ("cam_wrist_right", "wrist_right"),
                                 ("cam_wrist_left", "wrist_left")):
                    Image.fromarray(world.env.camera_rgb(cam)).save(os.path.join(od, f"{name}.png"))
            except Exception as ex:  # noqa: BLE001  (frames are diagnostic, never fail the episode on this)
                print("FRAME_SAVE_FAIL " + str(ex), flush=True)
        code = 0
    except Exception as ex:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        results.append({"ok": False, "status": f"{type(ex).__name__}: {ex}"})
        code = 1
    with open(os.path.join(a.out, "result.json"), "w") as f:
        json.dump(results, f, indent=1, default=_jsonable)
    print("DONE " + json.dumps({"n": len(results), "ok": sum(1 for r in results if r.get("ok"))}), flush=True)
    sys.exit(code)


if __name__ == "__main__":
    main()
