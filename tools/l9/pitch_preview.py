"""Franka head-camera pitch preview (pod, Isaac): for a few real production rows (one per scene family), build the
scene once (world.prepare), then ONLY change the head camera's pitch (same mast x/y/h/pan the episode actually
drew) and re-render -- no episode loop, no physics re-run between pitches. Saves one PNG per scene, panels side by
side labelled by pitch offset.
usage: python -m tools.l9.pitch_preview --plan P.json --out DIR [--offsets 0,5,10,15,20]
"""
from __future__ import annotations

import argparse
import json
import os


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--offsets", default="0,5,10,15,20")
    a = ap.parse_args(argv)
    code = 0
    try:
        from PIL import Image, ImageDraw

        from harvest.l9 import hcam9 as HC
        from harvest.l9 import reach9 as RM
        from harvest.l9.collect9 import draw as draw_scene
        from harvest.l9.rt9 import install as v2_install
        from harvest.l9.run9 import job_pool, rooms_for
        from harvest.l9.world9 import make_world9
        from harvest.teach_l8d.fx import SkipScene
        from harvest.l9.collect9 import NoEpisode

        os.makedirs(a.out, exist_ok=True)
        offsets = [float(x) for x in a.offsets.split(",")]
        rows = json.load(open(a.plan))
        rows_by_job = {}
        for r in rows:
            rows_by_job.setdefault(r["job"], []).append(r)
        rm = RM.load_default()
        results = []
        for job, jrows in rows_by_job.items():
            robot = jrows[0].get("robot") or "ffw_sg2"
            arm = jrows[0]["arm"]
            split = jrows[0].get("split", "train")
            pool = job_pool(jrows, robot, True, False)
            rooms = rooms_for(int(jrows[0]["rooms"]), "train" if split == "train" else "ood")
            world = make_world9(arm, pool, rooms, robot=robot, hcam=None)
            v2_install(world, robot, arm, allow_untested=False)
            done = False
            for row in jrows:  # try candidate rows for this family until one builds (NoEpisode: retry next)
                try:
                    sc, ep, light, head, h, sd = draw_scene(row, pool, rm, None, tries=20, world=world)
                    world.prepare(sc, ep, light, head, sd)
                except (NoEpisode, SkipScene) as ex:
                    print(f"SKIP_ROW {job} seed={row['seed']}: {ex}", flush=True)
                    continue
                base = dict(world.head_cam["draw"])
                p0 = float(base["pitch"])
                imgs = []
                for off in offsets:
                    d = dict(base, pitch=p0 - off)
                    pp, pq = world._parent_pose("cam_head")
                    R, t = HC.mast_pose(world.base["pos"], world.table_z, d)
                    pos, q = HC.mount_of(pp, pq, t, R)
                    world._write_mount("cam_head", [*pos, *q])
                    world._write_K("cam_head", d["hfov"])
                    world.env.env.sim.render()
                    world.env.env.sim.render()
                    rgb = world.env.camera_rgb("cam_head")[..., :3].copy()
                    im = Image.fromarray(rgb)
                    dr = ImageDraw.Draw(im)
                    dr.rectangle([0, 0, 120, 22], fill=(0, 0, 0))
                    dr.text((4, 4), f"pitch {p0 - off:.0f} (+{off:.0f})", fill=(255, 255, 0))
                    imgs.append(im)
                W, H = imgs[0].size
                comp = Image.new("RGB", (W * len(imgs), H))
                for i, im in enumerate(imgs):
                    comp.paste(im, (i * W, 0))
                out_path = os.path.join(a.out, f"{sc['family']}_{row['seed']}.png")
                comp.save(out_path)
                results.append({"family": sc["family"], "seed": row["seed"], "base_pitch": p0, "path": out_path})
                done = True
                break
            if not done:
                print(f"NO_ROW_WORKED {job}", flush=True)
            world.env.close()
        json.dump(results, open(os.path.join(a.out, "index.json"), "w"), indent=1)
        print("PITCH_PREVIEW " + json.dumps(results), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
