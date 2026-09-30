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


def draw(row: dict, pool: dict, rm, ledger=None, tries: int = 8, world=None) -> tuple:
    """(scene, ep, light family, head, combo hash, visual seed) for a plan row, or NoEpisode. With a world the combo
    record names the room / HDRI / materials the world will use (same draws), else their seed."""
    d = T9.DEFS[row["def"]]
    last = None
    for k in range(tries):
        sd = int(row["seed"]) + 100003 * k
        try:
            sc = S9.sample(row["family"], row["rule"], sd, row["arm"], rm)
        except RuntimeError as ex:
            last = str(ex)
            continue
        ep = T9.instantiate(d, sc, pool, sd, rm, tries=20)
        if ep is None:
            last = "definition does not fit the scene"
            continue
        T9.add_clutter(ep, sc, pool, sd, rm)
        light = V.pick_light_family(sd, row["family"])
        head = V.head_pose(sd)
        rp, hp = V.pose_key(sc["robot_pose"], head)
        parts = sc["furniture"]
        room = world.room_name(sd, sc["family"], parts) if world is not None else f"seed:{sd}"
        hdr = world.hdr_name(sd) if world is not None else f"seed:{sd}"
        mats = world.material_ids(sd, [p for p in parts if room is None or p["role"] != "room_wall"])             if world is not None else f"seed:{sd}"
        rec = {"room": room, "furniture": [sc["family"], sc["rule"], sc["params"], [p["size"] for p in sc["parts_s"]]],
               "materials": mats, "light_family": light, "hdr": hdr, "robot_pose": rp, "head_pose": hp}
        h = V.combo_hash(rec)
        if ledger is not None and ledger.seen(h):
            last = "combination already used"
            continue
        return sc, ep, light, head, h, sd
    raise NoEpisode(last)


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


def final_tilts(world, ep: dict) -> dict:
    from ..predicates import _tilt_deg
    out = {}
    for a, _, _ in ep["steps"]:
        q = np.asarray(world.env.object_pose(a)[1], float)
        out[a] = round(float(_tilt_deg(q)), 1)
    return out


def run_episode(world, row: dict, out_dir: str, pool: dict, rm, ledger=None, p: float = 0.35,
                stop_calls: int = 30, stop_motion_s: float = 120.0, video: bool = False) -> dict:
    from ..teach_l8d.collect import collect_episode
    sc, ep, light, head, h, sd = draw(row, pool, rm, ledger, world=world)
    register_task(ep)
    world.prepare(sc, ep, light, head, sd)
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
                decor=fs.get("decor"),
                motion_version=MOTION_VERSION, judge_l9=judge or None, plan_row=row)
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    with open(os.path.join(out_dir, "episode9.json"), "w") as f:
        json.dump({"scene": {k: v for k, v in sc.items() if k != "parts_s"}, "episode": ep}, f, default=str)
    lab = os.path.join(out_dir, "labels.jsonl")
    if os.path.exists(lab):
        rows = [json.loads(x) for x in open(lab)]
        with open(lab, "w") as f:
            for r in rows:
                f.write(json.dumps(dict(r, hand=row["arm"], gen=GEN)) + "\n")
    return meta
