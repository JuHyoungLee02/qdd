"""(pod) Articulated-skill collection runner: python -m harvest.l9art.run_art --plan plan.json --job J --out DIR
Plan rows {seed, def, robot, arm, split, job, pool, rooms, fx_seed}; one process = one (robot, arm, job): one fixture
per family (seeded by the job), every row of the job. Output <out>/<split>/<def>/<def>_s<seed>_<arm>[_<robot>]/
(calls/, labels.jsonl, meta.json, joints.npz, review.png); finished / skipped rows are not redone."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time

import numpy as np

OUT = "/data/harvest/l9v2/art_pilot/collect"
SCENE_TRIES = 3  # an episode skips only after 3 scene draws fail the visibility / IK checks


def ep_dir(out, r):
    rb = r.get("robot") or "ffw_sg2"
    tail = "" if rb == "ffw_sg2" else f"_{rb}"
    return os.path.join(out, r.get("split", "train"), r["def"], f"{r['def']}_s{r['seed']}_{r['arm']}{tail}")


def pick_objects(pool: dict, prog: dict, seed: int, robot: str) -> dict:
    """Task / prop objects: pushable = upright stable box-like targets; props = small clutter. -> {key: {name, fp, h}}"""
    from ..astra_motion import prompts as P
    rng = np.random.default_rng([int(seed), 3030])
    rows = []
    for k, v in sorted(pool.items()):
        he = v.get("half_extents")
        if not he or v.get("role9") == "container":
            continue
        dx, dy, h = 2 * float(he[0]), 2 * float(he[1]), 2 * float(he[2])
        name = str(P.OBJ_NAME.get(k, v.get("name", k)))
        rows.append((k, name, dx, dy, h, v))
    if prog.get("need_obj") == "pushable":
        base = [r for r in rows if r[4] <= 1.3 * min(r[2], r[3]) and 0.04 <= min(r[2], r[3]) and max(r[2], r[3]) <= 0.14
                and str(r[5].get("l9cat")) not in ("fruit", "vegetable", "bread", "can", "bottle", "cup", "mug", "bowl",
                                                   "jar", "vase", "flower", "plate", "spoon_fork")]
        cand = [r for r in base if r[5].get("l9cat") in ("box", "block", "book")]  # flat-sided only (smoke: a burger rolled, toppled)
    else:
        cand = [r for r in rows if max(r[2], r[3]) <= 0.14 and r[4] <= 0.16]
        if prog.get("need_obj") == "small":  # combo pick: grasp-tested L9 targets that fit a drawer
            cand = [r for r in cand if r[5].get("role9") == "target" and max(r[2], r[3]) <= 0.10 and r[4] <= 0.10
                    and min(r[2], r[3]) <= 0.06]
    if not cand:
        raise ValueError("no fitting object in the pool")
    out = {}
    for j in rng.permutation(len(cand))[: 1 + int(rng.integers(0, 2))]:
        k, name, dx, dy, h, _ = cand[int(j)]
        out[k] = {"name": name, "fp": (dx, dy), "h": h}
    return out


POOL_N = {"push": 6, "small": 6, "prop": 8}


def art_pool(job: str, robot: str) -> dict:
    """The job's objects (L9 train catalog): flat-sided push objects, small grasp-tested targets (combos), props.
    (smoke 10-02: L9 pick-place pools had no box / block in half the jobs -> push rows skipped)."""
    from ..l9 import assets9 as A9
    from ..l9 import robot9 as RB
    cat = A9.catalog("train")
    gmax = {"franka_mast": 0.066}.get(robot) or (float(RB.V2[robot]["grip_max_w"]) - 0.014 if robot in ("r1pro", "g1") else 0.093)

    def dims(v):
        he = v.get("half_extents") or [0.1, 0.1, 0.1]
        return 2 * float(he[0]), 2 * float(he[1]), 2 * float(he[2])
    push, small, prop = [], [], []
    for k, v in sorted(cat.items()):
        if v.get("role9") == "container":
            continue
        dx, dy, h = dims(v)
        if v.get("l9cat") in ("box", "block", "book") and h <= 1.3 * min(dx, dy) and 0.04 <= min(dx, dy) \
                and max(dx, dy) <= 0.14:
            push.append(k)
        if v.get("role9") == "target" and max(dx, dy) <= 0.10 and h <= 0.10 and min(dx, dy) <= min(0.06, gmax):
            small.append(k)
        if max(dx, dy) <= 0.14 and h <= 0.16:
            prop.append(k)
    rng = np.random.default_rng(int(hashlib.sha256(f"l9art-pool:{job}".encode()).hexdigest()[:8], 16))
    out = {}
    for lst, n in ((push, POOL_N["push"]), (small, POOL_N["small"]), (prop, POOL_N["prop"])):
        for j in rng.permutation(len(lst))[:n]:
            out[lst[int(j)]] = cat[lst[int(j)]]
    return out


def fx_seeds(job: str, arm: str = "right") -> dict:
    """One fixture seed per family for a job; the door hinges on the arm's side (smoke 10-02: a door hinged on the
    far side swung its handle out of reach / left no pre-pose for the close push)."""
    from .fixtures import FAMILIES, sample
    h = int(hashlib.sha256(f"l9art:{job}".encode()).hexdigest()[:8], 16)
    out = {f: (h + 7919 * i) % 100000 for i, f in enumerate(FAMILIES)}
    s = out["door"]
    while sample("door", s)["handles"]["door"]["hinge"] != arm:
        s += 1
    out["door"] = s
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--p", type=float, default=0.15)
    ap.add_argument("--video", action="store_true", help="per-episode review frames (head | wrist every 6 steps)")
    ap.add_argument("--diag-drift", action="store_true", help="diagnosis: passive joint drift of every fixture, no episodes")
    ap.add_argument("--video-seeds", default="", help="tools/l9/lane.sh passes it: review frames for these seeds only")
    a = ap.parse_args(argv)
    code = 0
    try:
        from ..l9 import assets9 as A9
        from ..l9 import run9 as R9run
        from ..l9 import vary9 as V
        from ..l9 import world9 as W9
        from ..l9.arm import apply_arm_workspace
        from ..l9.collect9 import register_task
        from ..l9.robot9 import apply_prompts
        from ..teach_l8d.collect import save_joints
        from ..teach_l8d.fx import SkipScene
        from . import episode_art as EA
        from . import fixtures as FX
        from . import scene_art as SA
        from . import tasks as TK
        from . import world_art as WA
        rows = [r for r in json.load(open(a.plan)) if str(r["job"]) == str(a.job)]
        if not rows:
            raise ValueError(f"no rows for job {a.job}")
        robot = rows[0].get("robot") or "ffw_sg2"
        arm = rows[0]["arm"]
        todo = [r for r in rows if not (os.path.exists(os.path.join(ep_dir(a.out, r), "meta.json"))
                                        or os.path.exists(os.path.join(ep_dir(a.out, r), "skipped.json")))]
        print("JOB " + json.dumps({"job": a.job, "rows": len(rows), "todo": len(todo)}), flush=True)
        if not todo:
            print("RUN_DONE", flush=True)
            os._exit(0)
        apply_arm_workspace(arm)
        apply_prompts(robot)
        pool = art_pool(a.job, robot)
        rooms = R9run.rooms_for(int(rows[0].get("rooms", 0)), "train")
        mesh = A9.mesh_for(int(rows[0].get("rooms", 0)), split="train")
        seeds = rows[0].get("fx_seed") or fx_seeds(a.job, arm)
        specs = {f: FX.sample(f, int(s)) for f, s in seeds.items()}
        world = WA.make_art_world(arm, pool, rooms, mesh, robot, specs)
        ex = EA.Exec(world, robot, arm)
        print("WORLD " + json.dumps({"robot": robot, "arm": arm, "fixtures": {f: s["name"] for f, s in specs.items()},
                                     "pool": len(pool), "n": len(todo)}), flush=True)
        if a.diag_drift:  # passive joint drift test: each fixture's joints at mid-range, no contact
            import torch
            for r in todo[:1]:
                for fam, spec in specs.items():
                    seed = int(r["seed"])
                    prog = {"def": "diag", "stages": [], "start": {}, "instruction": "diag", "need_obj": None}
                    objs = pick_objects(pool, prog, seed, robot)
                    T = SA.T_WF(0.55, -0.2 * SA.side(arm), 0.75, 0.0)
                    built = SA.build(seed, robot, arm, None, prog, objs)
                    built["sc"]["furniture"][0]["pos"][2] = built["sc"]["furniture"][0]["pos"][2]
                    T[2, 3] = built["tz"]
                    W9._ART_GHOST = WA.ghost_part(spec, T)
                    register_task(built["ep"])
                    world.prepare(built["sc"], built["ep"], V.pick_light_family(seed, "office"), V.head_pose(seed), seed)
                    mid = {jn: 0.5 * (J["lo"] + J["hi"]) if J["kind"] != "knob" else 0.5 for jn, J in spec["joints"].items()}
                    WA.stage_fixture(world, fam, T, mid)
                    world.reset(seed)
                    ex.reset()
                    st0 = WA.settle_fixture(world, mid)
                    art = world.env.scene[world.fx[fam]["key"]]
                    series = []
                    for k in range(120):
                        ex.step()
                        if k % 20 == 0:
                            series.append({jn: round(v, 4) for jn, v in WA.joints(world).items()})
                    print("DRIFT " + json.dumps({"fam": fam, "mid": {k: round(v, 4) for k, v in mid.items()},
                                                 "settle": {k: round(v, 4) for k, v in st0["joints"].items()},
                                                 "series": series,
                                                 "stiffness": art.data.joint_stiffness[0].cpu().numpy().round(3).tolist(),
                                                 "damping": art.data.joint_damping[0].cpu().numpy().round(3).tolist(),
                                                 "root_err": round(st0["root_err_m"], 4)}), flush=True)
            print("RUN_DONE", flush=True)
            os._exit(0)
        for r in todo:
            od = ep_dir(a.out, r)
            t0 = time.perf_counter()
            seed = int(r["seed"])
            try:
                d = TK.DEFS[r["def"]]
                fam = d["family"]
                spec = specs.get(fam) if fam != "none" else None
                prog0 = TK.instantiate(r["def"], spec, seed)
                objs = pick_objects(pool, prog0, seed, robot)
                prog = TK.instantiate(r["def"], spec, seed, obj_name=next(iter(objs.values()))["name"])
                why_all = []
                for tr in range(SCENE_TRIES):  # redraw the scene (placement / head) when a check fails
                    try:
                        built = SA.build(seed + 1000003 * tr, robot, arm, spec, prog, objs)
                        sc, ep = built["sc"], built["ep"]
                        T = np.asarray(built["fixture"]["T"]) if built["fixture"] else None
                        W9._ART_GHOST = WA.ghost_part(spec, T) if spec is not None else None
                        register_task(ep)
                        light = V.pick_light_family(seed, sc["family"])
                        sd = seed + 1000003 * tr
                        head = SA.head_aim(sd, built["p_int"], sc["lift"]) if robot == "ffw_sg2" else V.head_pose(sd)
                        world.prepare(sc, ep, light, head, sd)
                        WA.stage_fixture(world, fam if spec is not None else None, T, prog["start"])
                        world.reset(sd)
                        ex.reset()
                        fx_state = WA.settle_fixture(world, prog["start"]) if spec is not None else {}
                        if spec is not None and fx_state.get("root_err_m", 0) > 0.01:
                            raise SkipScene(f"fixture root off by {fx_state['root_err_m']:.3f} m")
                        os.makedirs(od, exist_ok=True)
                        vid = a.video or str(seed) in {s.strip() for s in a.video_seeds.split(",") if s.strip()}
                        epi = EA.ArtEpisode(world, ex, r, built, spec, prog, od, p=a.p, video=vid)
                        obs = world.observe(depth=False)
                        why = epi.unseen(obs.cams["head"])
                        if why:
                            raise SkipScene(f"outside the head image: {why}")
                        why = epi.precheck()
                        if why:
                            raise SkipScene(f"IK precheck: {why}")
                        break
                    except SkipScene as e1:
                        why_all.append(str(e1)[:80])
                        if tr == SCENE_TRIES - 1:
                            raise SkipScene(" | ".join(why_all))
                res = epi.run()
            except (SkipScene, ValueError, KeyError) as e:
                os.makedirs(od, exist_ok=True)
                json.dump({"row": r, "reason": f"{type(e).__name__}: {e}"}, open(os.path.join(od, "skipped.json"), "w"))
                print("SKIP " + json.dumps({"seed": seed, "def": r["def"], "reason": str(e)[:200],
                                            "wall_s": round(time.perf_counter() - t0, 1)}), flush=True)
                continue
            meta = dict(res, seed=seed, task_id=r["def"], skill=[s["skill"] for s in prog["stages"]],
                        skills_v3=sorted({s["skill"] for s in prog["stages"]}), robot=robot, arm=arm,
                        split=r.get("split", "train"), instruction=prog["instruction"], words=prog["words"],
                        prog={"stages": prog["stages"], "start": prog["start"], "judge": prog["judge"], "links": prog["links"]},
                        fixture=None if spec is None else {"name": spec["name"], "family": spec["family"],
                                                           "seed": spec["seed"], "dims": spec["dims"],
                                                           "pose": built["fixture"], "label": spec.get("label"),
                                                           "joints": {k: {kk: J[kk] for kk in ("type", "kind", "lo", "hi", "drive")}
                                                                      for k, J in spec["joints"].items()},
                                                           "handles": {k: {kk: h.get(kk) for kk in ("type", "words", "length", "thick", "standoff", "face")}
                                                                       for k, h in spec["handles"].items()}},
                        fixture_settle=fx_state, objects=built["ep"]["names"], tz=built["tz"], z_int=built["z_int"],
                        lift=sc["lift"], env_family=sc["family"], room=(world.furniture_scene or {}).get("room"),
                        hdr=getattr(world, "hdr", None), head_pose=(world.furniture_scene or {}).get("head"),
                        head_cam=getattr(world, "head_cam", None), gen="l9art", gen_version="v3",
                        format_version="v3", label_origin="l9art", motion_version=EA.VERSION, plan_row=r,
                        cmd_dq_cap=EA.CMD_DQ, planner_stats=dict(ex.stats), p=a.p)
            save_joints(world, od, meta)
            with open(os.path.join(od, "labels.jsonl"), "w") as f:
                for x in epi.rows:
                    f.write(json.dumps(dict(x, seed=seed, task=r["def"], hand=arm, gen="l9art")) + "\n")
            json.dump(meta, open(os.path.join(od, "meta.json"), "w"), default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
            if ex.frames:
                _review(ex.frames, od)
            keep = ("seed", "task_id", "robot", "success", "end_reason", "n_calls", "max_dq_rad", "wall_s", "fail_counts")
            print("EP " + json.dumps(dict({k: meta.get(k) for k in keep}, wall_total_s=round(time.perf_counter() - t0, 1))),
                  flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


def _review(frames, od, cols: int = 6, rows: int = 4):
    """A contact sheet (24 evenly spaced head | wrist frames) + an mp4 when cv2 is present."""
    from PIL import Image
    n = len(frames)
    idx = np.linspace(0, n - 1, min(n, cols * rows)).astype(int)
    tiles = []
    for i in idx:
        h, w_ = frames[i]
        hi = Image.fromarray(np.asarray(h)[..., :3]).resize((336, 188))
        wi = Image.fromarray(np.asarray(w_)[..., :3]).resize((212, 120))
        t = Image.new("RGB", (336, 308))
        t.paste(hi, (0, 0))
        t.paste(wi, (62, 188))
        tiles.append(t)
    sheet = Image.new("RGB", (336 * cols, 308 * math.ceil(len(tiles) / cols)))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % cols) * 336, (k // cols) * 308))
    sheet.save(os.path.join(od, "review.jpg"), quality=80)
    try:
        import cv2
        h0 = np.asarray(frames[0][0])
        vw = cv2.VideoWriter(os.path.join(od, "head.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 10, (h0.shape[1], h0.shape[0]))
        for h, _ in frames:
            vw.write(cv2.cvtColor(np.asarray(h)[..., :3], cv2.COLOR_RGB2BGR))
        vw.release()
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
