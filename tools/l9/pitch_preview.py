"""Franka head-camera pitch preview (pod, Isaac): for a few real production rows (one per scene family), build the
scene once (draw -> register_task -> prepare -> world.reset, the same order as collect9.run_episode), then ONLY
change the head camera's pitch (same mast x/y/h/pan/hfov the episode drew) and re-render -- no episode loop, no
physics between pitches. Panel 0 = PITCH_OLD_STEEPEST (the current, steepest-down angle = the lowest limit, user
10-03), panel k = k*5 deg further up toward horizontal. One PNG per scene, panels side by side.
usage: python -m tools.l9.pitch_preview --plan P.json --out DIR [--offsets 0,5,10,15,20] [--job pv_office]
10-03 fix: the old version never called world.reset (prepare() only stores the draw) and installed the rt9
planner it does not need; it sat 75 min with no output on a CPU-saturated pod. One job per process (env.close()
ends the Isaac app), RUN_DONE at the end for the isaac.sh watchdog, timestamps per stage.
"""
from __future__ import annotations

import argparse
import json
import os
import time

T0 = time.time()


def _log(msg: str) -> None:
    print(f"PV {time.time() - T0:7.1f}s {msg}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--offsets", default="0,5,10,15,20")
    ap.add_argument("--job", default="", help="only this plan job (one Isaac process per job)")
    ap.add_argument("--max-rows", type=int, default=1, help="PNGs per job")
    a = ap.parse_args(argv)
    code = 0
    try:
        from PIL import Image, ImageDraw

        from harvest.l9 import hcam9 as HC
        from harvest.l9 import reach9 as RM
        from harvest.l9.collect9 import NoEpisode, register_task
        from harvest.l9.collect9 import draw as draw_scene
        from harvest.l9.run9 import job_pool, rooms_for
        from harvest.l9.world9 import make_world9
        from harvest.teach_l8d.fx import SkipScene

        os.makedirs(a.out, exist_ok=True)
        offsets = [float(x) for x in a.offsets.split(",")]
        rows = [r for r in json.load(open(a.plan)) if not a.job or r["job"] == a.job]
        if not rows:
            raise SystemExit(f"no plan rows for job {a.job!r}")
        jobs = {r["job"] for r in rows}
        if len(jobs) != 1:
            raise SystemExit(f"one job per process (env.close ends the app), got {sorted(jobs)}: pass --job")
        job = rows[0]["job"]
        robot = rows[0].get("robot") or "ffw_sg2"
        arm = rows[0]["arm"]
        split = rows[0].get("split", "train")
        rm = RM.load_default()
        pool = job_pool(rows, robot, True, False)
        rooms = rooms_for(int(rows[0]["rooms"]), "train" if split == "train" else "ood")
        _log(f"world build {job} robot={robot} arm={arm}")
        world = make_world9(arm, pool, rooms, robot=robot, hcam=None)
        _log("world ready")
        results = []
        for row in rows:  # candidate rows of this family until max_rows build (NoEpisode / SkipScene: next)
            if len(results) >= a.max_rows:
                break
            try:
                sc, ep, light, head, h, sd = draw_scene(row, pool, rm, None, tries=20, world=world)
                _log(f"drawn seed={row['seed']} family={sc['family']} rule={sc['rule']}")
                register_task(ep)
                world.prepare(sc, ep, light, head, sd)
                world.reset(int(row["seed"]))
                _log(f"reset done seed={row['seed']}")
            except (NoEpisode, SkipScene) as ex:
                _log(f"SKIP_ROW seed={row['seed']}: {ex}")
                continue
            if not world.head_cam or not world.head_cam.get("draw"):
                _log(f"SKIP_ROW seed={row['seed']}: head_cam not drawn after reset")
                continue
            base = dict(world.head_cam["draw"])
            p0 = float(HC.PITCH_OLD_STEEPEST)  # the current angle = the lowest limit; offsets go up from it
            imgs = []
            for off in offsets:
                d = dict(base, pitch=p0 - off)
                pp, pq = world._parent_pose("cam_head")
                R, t = HC.mast_pose(world.base["pos"], world.table_z, d)
                pos, q = HC.mount_of(pp, pq, t, R)
                world._write_mount("cam_head", [*pos, *q])
                world._write_K("cam_head", d["hfov"])
                for _ in range(3):
                    world.env.env.sim.render()
                rgb = world.env.camera_rgb("cam_head")[..., :3].copy()
                im = Image.fromarray(rgb)
                dr = ImageDraw.Draw(im)
                dr.rectangle([0, 0, 190, 22], fill=(0, 0, 0))
                dr.text((4, 4), f"pitch {p0 - off:.0f} down (+{off:.0f} up)", fill=(255, 255, 0))
                imgs.append(im)
            W, H = imgs[0].size
            comp = Image.new("RGB", (W * len(imgs), H))
            for i, im in enumerate(imgs):
                comp.paste(im, (i * W, 0))
            out_path = os.path.join(a.out, f"{sc['family']}_{row['seed']}.png")
            comp.save(out_path)
            results.append({"job": job, "family": sc["family"], "rule": sc["rule"], "seed": row["seed"],
                            "base_pitch": p0, "offsets": offsets, "mast": {k: base.get(k) for k in
                                                                           ("x", "y", "h", "pan", "hfov")},
                            "path": out_path})
            _log(f"PNG {out_path}")
        if not results:
            _log(f"NO_ROW_WORKED {job}")
        json.dump(results, open(os.path.join(a.out, f"index_{job}.json"), "w"), indent=1)
        print("PITCH_PREVIEW " + json.dumps(results), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    print("RUN_DONE", flush=True)  # isaac.sh watchdog: kill the tree 90 s later if os._exit does not end Isaac (P190)
    os._exit(code)


if __name__ == "__main__":
    main()
