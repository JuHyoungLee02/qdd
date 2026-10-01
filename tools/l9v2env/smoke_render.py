"""L9 v2 environment render smoke (pod, Isaac via tools/l9/isaac.sh): for the rows of one job (tools/l9v2env/
smoke_rows.py) draw the episode exactly like production (collect9.draw: scene, task, clutter, light, head, combo),
build it in a World9 (reset: furniture, room, materials, decor, HDRI, lights, neck in-view redraw) and save the head
camera's first frame (no episode is run) + a json line per frame. Works on the v1 code too (baseline).
usage: isaac.sh CODE 1 TAG tools.l9v2env.smoke_render --rows ROWS.json --job s000 --out DIR"""
from __future__ import annotations

import argparse
import json
import os
import time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--wrist", action="store_true")
    a = ap.parse_args(argv)
    code = 0
    try:
        import numpy as np
        from PIL import Image

        from harvest.l9 import assets9 as A9
        from harvest.l9 import reach9 as R9
        from harvest.l9.arm import apply_arm_workspace
        from harvest.l9.collect9 import NoEpisode, draw, register_task
        from harvest.l9.run9 import rooms_for
        from harvest.l9.world9 import make_world9
        from harvest.teach_l8d.fx import SkipScene
        rows = [r for r in json.load(open(a.rows)) if r["job"] == a.job]
        os.makedirs(a.out, exist_ok=True)
        arm = rows[0]["arm"]
        apply_arm_workspace(arm)
        pool = A9.pool_for(int(rows[0]["pool"]), "train")
        rooms = rooms_for(int(rows[0]["rooms"]), "train")
        mesh = A9.mesh_for(int(rows[0]["rooms"]), split="train")
        t0 = time.time()
        world = make_world9(arm, pool, rooms, mesh=mesh)
        from harvest.teach_l8d import collect as _c  # noqa: F401
        apply_arm_workspace(arm)
        print("WORLD " + json.dumps({"job": a.job, "arm": arm, "rows": len(rows), "start_s": round(time.time() - t0, 1)}),
              flush=True)
        rm = R9.load_default()
        log = open(os.path.join(a.out, f"frames_{a.job}.jsonl"), "a")
        for r in rows:
            name = f"{r['family']}__{r['rule']}__s{r['seed']}_{r['arm']}"
            if os.path.exists(os.path.join(a.out, name + "_head.png")):
                continue
            t1 = time.time()
            try:
                sc, ep, light, head, h, sd = draw(r, pool, rm, None, tries=10, world=world)
                register_task(ep)
                world.prepare(sc, ep, light, head, sd)
                world.reset(int(r["seed"]))
                world._render()
                img = world.env.camera_rgb("cam_head")[..., :3]
                Image.fromarray(np.asarray(img, np.uint8)).save(os.path.join(a.out, name + "_head.png"))
                if a.wrist:
                    from harvest.l9 import arm as AR
                    Image.fromarray(np.asarray(world.env.camera_rgb(AR.wrist_camera(arm))[..., :3], np.uint8)).save(
                        os.path.join(a.out, name + "_wrist.png"))
                fs = world.furniture_scene or {}
                rec = {"name": name, "row": r, "ok": True, "s": round(time.time() - t1, 1), "room": fs.get("room"),
                       "hdr": fs.get("hdr"), "light": fs.get("light_family"), "head": fs.get("head"),
                       "materials": fs.get("materials"), "decor": fs.get("decor"), "env_axes": fs.get("env_axes"),
                       "instruction": ep.get("instruction"), "lift": sc.get("lift"), "iso": fs.get("iso")}
            except (SkipScene, NoEpisode, ValueError, RuntimeError, KeyError) as ex:
                rec = {"name": name, "row": r, "ok": False, "err": f"{type(ex).__name__}: {ex}"[:300]}
            log.write(json.dumps(rec, default=str) + "\n")
            log.flush()
            print("FRAME " + json.dumps({k: rec.get(k) for k in ("name", "ok", "s", "err")}), flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
