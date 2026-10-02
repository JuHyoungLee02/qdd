"""L9 episode = the L8S collection path (teach_l8d.collect.collect_episode: XCollector truth labels + DART-style
perturbations, PtEpisode / XEpisode, calls/, labels.jsonl, joints.npz, scene.json, meta.json) on a World9, plus:
  draw     scene9 (family, layout rule, arm) -> task9 definition -> clutter -> light family / head pose, redrawn while
           the definition does not fit the scene or the environment combination was already used (vary9 ledger)
  register the episode's task (tasks.TASKS / X_TASKS, X_STEPS for multi-step) under L9_TASK
  judge    insert definitions: the object's tilt <= 15 deg at the end (spec §3), on top of success_now
  record   meta gen / env_family / layout / task_family / task_id / arm / head_pose / light_family / unreal /
           combo_hash / robot_pose / objects; every labels row gets `hand` (spec §4)."""
from __future__ import annotations

import json
import os

import numpy as np

from . import scene9 as S9
from . import task9 as T9
from . import vary9 as V

GEN = "l9"
MOTION_VERSION = "l8s-1"  # the L8S truth plan / executor (human-like motion variation: a later code swap, §10)


class NoEpisode(Exception):
    pass


def draw(row: dict, pool: dict, rm, ledger=None, tries: int = 20, world=None) -> tuple:
    """(scene, ep, light family, head, combo hash, visual seed) for a plan row, or NoEpisode. With a world the combo
    record names the room / HDRI / materials the world will use (same draws), else their seed."""
    d = T9.get_def(row["def"])
    last = None
    for k in range(tries):
        sd = int(row["seed"]) + 100003 * k
        try:
            rmx = rm
            if row.get("reach") == "base":  # diagnosis rows: the L8S reach probe / default lift
                from . import reach9 as R9
                rmx = R9.load_base()
            sc = S9.sample(row["family"], row["rule"], sd, row["arm"], rmx,
                           lifts=[S9.LIFT_DEFAULT] if row.get("lift_mode") == "default" else None,
                           robot=row.get("robot"))  # L9v2-R1: r1pro may use its own reach band (scene9.usable)
        except RuntimeError as ex:
            last = str(ex)
            continue
        ep = T9.instantiate(d, sc, pool, sd, rmx, tries=20, fixed=row.get("fixed"), grip_max=row.get("grip_max"),
                            v2=bool(row.get("v2")))  # L9 v2 rows: robot max opening, step info (task9v2)
        if ep is None:
            last = "definition does not fit the scene"
            continue
        robot = row.get("robot") or "ffw_sg2"
        if robot in ("g1", "r1pro"):  # body reach band (world9._place_v2 skips the scene): draw another scene instead
            from . import robot9 as RB  # of losing the row (G1 pilot 10-02: 58 of 60 rows skipped)
            ok = RB.g1_surface_ok(ep["table_z"]) if robot == "g1" else RB.r1_surface_ok(ep["table_z"])
            if not ok:
                last = f"{robot}: surface {float(ep['table_z']):.2f} m outside its reach band"
                continue
        T9.add_clutter(ep, sc, pool, sd, rmx, grip_max=row.get("grip_max"))
        light = V.pick_light_family(sd, row["family"])
        head = V.head_pose(sd)
        rp, hp = V.pose_key(sc["robot_pose"], head)
        parts = sc["furniture"]
        room = world.room_name(sd, sc["family"], parts) if world is not None else f"seed:{sd}"
        hdr = world.hdr_name(sd, sc["family"]) if world is not None else f"seed:{sd}"
        mats = world.material_ids(sd, [p for p in parts if room is None or p["role"] != "room_wall"])             if world is not None else f"seed:{sd}"
        tag = combo_tag(row)
        if tag:  # spec §9: another robot / a drawn head camera is another combination (AI Worker std: unchanged)
            hp = list(hp) + [tag]
        rec = {"room": room, "furniture": [sc["family"], sc["rule"], sc["params"], [p["size"] for p in sc["parts_s"]]],
               "materials": mats, "light_family": light, "hdr": hdr, "robot_pose": rp, "head_pose": hp}
        h = V.combo_hash(rec)
        if ledger is not None and ledger.seen(h):
            last = "combination already used"
            continue
        return sc, ep, light, head, h, sd
    raise NoEpisode(last)


def combo_tag(row: dict) -> str:
    """'' for the AI Worker with the standard head camera (old hashes unchanged), else robot / head-camera mode."""
    from .hcam9 import coin
    robot = row.get("robot") or "ffw_sg2"
    h = row.get("hcam")
    mode = coin(int(row["seed"])) if h == "coin" else (h or "std")
    return "" if (robot == "ffw_sg2" and mode == "std") else f"{robot}/{mode}"


def register_task(ep: dict) -> None:
    from ..sim import tasks as T
    steps = ep["steps"]
    t = T.Task(T9_TASK, steps[0][0], steps[0][1], ep["instruction"], {})
    T.TASKS[T9_TASK] = T.X_TASKS[T9_TASK] = t
    if len(steps) > 1:
        T.X_STEPS[T9_TASK] = tuple((a, p, tuple(o) if o else None) for a, p, o in steps)
    else:
        T.X_STEPS.pop(T9_TASK, None)


T9_TASK = "l9_task"


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return str(o)


def final_tilts(world, ep: dict) -> dict:
    from ..predicates import _tilt_deg
    out = {}
    for a, _, _ in ep["steps"]:
        q = np.asarray(world.env.object_pose(a)[1], float)
        out[a] = round(float(_tilt_deg(q)), 1)
    return out


def run_episode(world, row: dict, out_dir: str, pool: dict, rm, ledger=None, p: float = 0.35,
                stop_calls: int = 30, stop_motion_s: float = 120.0, video: bool = False, motion: bool = False) -> dict:
    from ..teach_l8d.collect import collect_episode
    sc, ep, light, head, h, sd = draw(row, pool, rm, ledger, tries=int(row.get("draw_tries", 20)), world=world)
    register_task(ep)
    world.prepare(sc, ep, light, head, sd)
    mstyle = None
    if motion:  # spec §10 human-like motion (opt-in per process; harvest.l9.motion9)
        from .motion9 import sample_style
        mstyle = sample_style(int(row["seed"]))
    world.motion = mstyle
    rt = getattr(world, "rt", None)
    if rt is not None:  # spec §12 v2: the cuRobo executor's timing style
        rt.style = mstyle
    style = "clean" if row.get("clean") else row.get("style", "")
    meta = collect_episode(world, int(row["seed"]), T9_TASK, "drf", row.get("split", "train"), out_dir,
                           0.0 if style == "clean" else p, 4, stop_calls, stop_motion_s, style, video=video)
    judge = {}
    if ep.get("judge", {}).get("upright_max_deg") is not None:
        tl = final_tilts(world, ep)
        judge = {"tilt_deg": tl, "upright_max_deg": ep["judge"]["upright_max_deg"],
                 "ok": all(v <= ep["judge"]["upright_max_deg"] for v in tl.values())}
        meta["success"] = bool(meta["success"] and judge["ok"])
    if ledger is not None:
        ledger.add(h)
    fs = getattr(world, "furniture_scene", {}) or {}
    meta.update(gen=GEN, env_family=sc["family"], layout=f"{sc['family']}/{sc['rule']}", layout_rule=sc["rule"],
                task_family=ep["family"], task_id=ep["def"], arm=row["arm"], head_pose=fs.get("head", head),
                light_family=light, unreal=False, combo_hash=h, robot_pose=sc["robot_pose"], lift_l9=sc["lift"],
                instruction=ep["instruction"], template=ep["template"], n_steps=len(ep["steps"]),
                objects={k: {"name": ep["names"].get(k), "node": o["node"]} for k, o in ep["objects"].items()},
                clutter=sorted(ep.get("clutter", {})), room=(fs.get("room") or {}).get("name"), hdr=fs.get("hdr"),
                materials=sorted(set((fs.get("materials") or {}).values())), iso=fs.get("iso"),
                decor=fs.get("decor"), robot=row.get("robot") or "ffw_sg2", head_cam=fs.get("head_cam"),
                base=fs.get("base"),
                motion_version=(mstyle or {}).get("version", MOTION_VERSION), motion_style=mstyle,
                judge_l9=judge or None, plan_row=row)
    if rt is not None:
        from .rt9 import VERSION as V2_VERSION
        gv = rt.episode_meta()
        from .specgate9 import SPEC, SPEC_FRANKA_R1
        meta.update(grasp_v2=gv, motion_version=V2_VERSION, label_origin="l9v2", gen_version="v2",
                    instruction=ep["instruction"] + gv.get("instruction_suffix", ""),
                    # frozen label spec (L9_PRINCIPLES §0); Franka rows get the r1 camera revision tag
                    # (specgate9.SPEC_FAMILY keeps the build gate's "one spec version" check passing)
                    spec_version=SPEC_FRANKA_R1 if (row.get("robot") == "franka_mast") else SPEC)
    else:
        meta.update(gen_version="v1", label_origin="v1")
    if ep.get("task_v2"):  # L9 v2 task fields (task9v2.finish): grasp-label scene constraints, place pose / height,
        # done predicates, instruction variant, recovery tags
        meta.update({k: ep.get(k) for k in ("step_info", "done", "instr_meta", "movable_containers", "start_poses",
                                              "recovery_candidate",
                                              "requires")})
    xm =world.ext_meta() if hasattr(world, "ext_meta") else {}
    if xm:  # paired external cameras (ext9); unpaired episodes get no key
        meta.update(xm)
    if os.environ.get("IR_L9_EXT_TIMING") == "1" and hasattr(world, "ext_timing"):
        print("EXTT " + json.dumps(dict(world.ext_timing(), seed=row["seed"], n_calls=meta.get("n_calls"),
                                        wall_s=meta.get("wall_s"))), flush=True)
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f, default=_json_default)
    with open(os.path.join(out_dir, "episode9.json"), "w") as f:
        json.dump({"scene": {k: v for k, v in sc.items() if k != "parts_s"}, "episode": ep}, f, default=str)
    lab = os.path.join(out_dir, "labels.jsonl")
    if os.path.exists(lab):
        rows = [json.loads(x) for x in open(lab)]
        with open(lab, "w") as f:
            for r in rows:
                f.write(json.dumps(dict(r, hand=row["arm"], gen=GEN)) + "\n")
    return meta
