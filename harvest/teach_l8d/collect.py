"""L8-D collection (prereg_l8d.md §2): the E-PT collection path (teach_pt.collect.PtCollector inside a PtEpisode: the
L8 behaviour policy = truth labels + DART-style perturbations, depth on; every call saves the astra-solo@v2 request
(prompt_v2.txt + grid overlay PNG), the three no-grid ND requests (+ ring-only PNG), the point request, head depth and
cameras) so the training format (grid on/off, hand-given info on/off, depth on/off) is chosen at build time.
Per episode it adds scene.json: table height, lift, workspace box, variant, task, layout, randomization (materials,
lights, distractors with the settled offsets) and the distractor count. Pure except the world handed in."""
from __future__ import annotations

import json
import os

import numpy as np

from ..astra_solo.pt_episode import PtEpisode
from ..teach_l8 import collect as LC
from ..teach_pt.collect import PtCollector

SCENE_SCHEMA = "qdd.l8d.scene/v1"


def _jl(v):
    if isinstance(v, dict):
        return {str(k): _jl(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jl(x) for x in v]
    if isinstance(v, (np.floating, float)):
        return round(float(v), 5)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.ndarray):
        return _jl(v.tolist())
    return v


def distractor_count(layout: dict, info: dict, randomization: dict | None) -> dict:
    """Obstacles on the table: layout objects other than target / place (the scene's o3 / o5 / o8 / o9) + pool
    distractors actually placed (randomize.sample_randomization)."""
    lay = [k for k in layout if k not in (info["tgt"], info["place"])]
    pool = [d["name"] for d in ((randomization or {}).get("distractors") or [])]
    return {"n": len(lay) + len(pool), "layout_objects": lay, "pool_distractors": pool}


def scene_record(world, seed: int, task: str, variant: str, split: str, style: str) -> dict:
    env = world.env
    info = world.task_info()
    rand = getattr(env, "randomization", None)
    return _jl({"schema": SCENE_SCHEMA, "seed": seed, "split": split, "task": task, "variant": variant,
                "style": style, "instruction": info["instruction"], "table_z": float(env.table_top_z),
                "lift": getattr(env, "lift", None), "ws": getattr(env, "ws", None), "layout": dict(env.layout),
                "randomization": rand, "rand_settle": getattr(env, "rand_settle", None),
                "distractors": distractor_count(env.layout, info, rand)})


def collect_episode(world, seed: int, task: str, variant: str, split: str, out_dir: str, p: float,
                    max_perturb: int = 4, stop_calls: int | None = 30, stop_motion_s: float | None = 120.0,
                    style: str = "", video: bool = False) -> dict:
    """= teach_pt.collect.collect_episode (same rng stream, collector, limits) + scene.json and an optional sparse
    video (Episode video=True: head | right wrist jpgs every 5 control ticks)."""
    rng = np.random.default_rng([int(seed), 8, LC.VARIANT_CODE.get(variant, 9)])
    coll = PtCollector(world, rng, p, max_perturb)
    ep = PtEpisode(world, coll, seed, task, out_dir, variant=variant, stop_calls=stop_calls,
                   stop_motion_s=stop_motion_s, allow_eef=True, save_v2=True, save_nd=True, video=video)
    coll.ep = ep
    res = ep.run()
    os.makedirs(out_dir, exist_ok=True)
    scene = scene_record(world, seed, task, variant, split, style)
    with open(os.path.join(out_dir, "scene.json"), "w") as f:
        json.dump(scene, f)
    with open(os.path.join(out_dir, "labels.jsonl"), "w") as f:
        for r in coll.rows:
            f.write(json.dumps(dict(r, seed=seed, task=task, variant=variant, table_z=scene["table_z"],
                                    n_distractors=scene["distractors"]["n"])) + "\n")
    meta = {"seed": seed, "split": split, "task": task, "variant": variant, "table_z": scene["table_z"],
            "lift": scene["lift"], "n_distractors": scene["distractors"]["n"], "p": p, "max_perturb": max_perturb,
            "style": style, "success": bool(res.get("success")), "end_reason": res.get("end_reason"),
            "n_calls": res["n_calls"], "n_rows": len(coll.rows), "n_perturb": coll.n_pert, "sim_t": res.get("sim_t"),
            "wall_s": res.get("wall_s"), "n_pt_labels": sum(r.get("pt_answer") is not None for r in coll.rows)}
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    return meta
