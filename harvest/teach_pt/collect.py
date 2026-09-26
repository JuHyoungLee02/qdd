"""E-PT collection (prereg_pt.md §2-3): the E-TEACH-L8 behaviour collection (teach_l8.collect: the same Collector,
behaviour policy, seeds -> the same states) run inside a PtEpisode, so each call saves the pt request (prompt.txt),
the v2 request of the same state (prompt_v2.txt), the two PNGs, the head z-depth and the cameras; the collector row
gets the pt truth label (pt_truth.pt_command: pixel verified against the depth, None = dropped), the pixels of the
TCP and objects, and the robot-side state the resolver needs offline (holding, grip offset, plane).
Splits: train (R2_TRAIN 10000-59999, standard / dr), dev (DEV 0-19, standard / dr, mug_tray = L8's DEV), ood_d
(DEV 20-29, variant random only = the TEST appearance pool, evaluation only; mug_tray), ood_h (DEV 0-19, standard,
table top 0.82 or 0.88 m instead of 0.85 = unseen table heights, evaluation only; mug_tray)."""
from __future__ import annotations

import json
import os

import numpy as np

from ..astra_solo.pt_episode import PtEpisode
from ..astra_solo.nd import est_label, nd_pt_command
from ..astra_solo.pt_truth import pixels_of, pt_command
from ..teach_l8 import collect as LC

OOD_D_SEEDS = range(20, 30)


OOD_H_TABLES = (0.82, 0.88)  # E-PT OOD-H (inside diversity_plan's OOD-H bands; training saw 0.85 only)


def check_seed(seed: int, split: str, variant: str, table_z: float | None = None) -> int:
    s = int(seed)
    if split == "ood_h":
        if s not in LC.DEV_SEEDS or variant != "standard" or table_z not in OOD_H_TABLES:
            raise ValueError(f"ood_h = DEV seeds 0-19, variant standard, table_z in {OOD_H_TABLES}")
        return s
    if table_z is not None:
        raise ValueError("table_z is only for split ood_h")
    if split == "ood_d":
        if s not in OOD_D_SEEDS or variant != "random":
            raise ValueError(f"ood_d = DEV seeds 20-29 with variant random only (seed {s}, {variant})")
        return s
    if variant == "random":
        raise ValueError("variant random (TEST pool) is evaluation only: split ood_d")
    return LC.check_seed(s, split)


def task_of(seed: int, split: str) -> str:
    return "mug_tray" if split in ("dev", "ood_d", "ood_h") else LC.task_of(seed, split)


class PtCollector(LC.Collector):
    name = "pt_behavior"

    def ask(self, text, images, meta):
        rep = super().ask(text, images, meta)
        row, ep, w = self.rows[-1], self.ep, self.w
        st = w.status()
        row["pixels"] = pixels_of(ep.head, st, ep.info)
        row["pt_state"] = {"holding": ep.holding(st), "grip_offset": ep.grip_offset, "plane": round(ep.plane, 4)}
        row["pt_answer"], row["pt_meta"], row["ndest_answer"], row["ndpt_answer"] = None, None, None, None
        if row.get("answer"):
            a = json.loads(row["answer"])
            c, m = pt_command(row["step"], a["command"], st, ep.info, ep.head, ep.depth, w.table_z)
            row["pt_meta"] = m
            if c is not None:
                row["pt_answer"] = json.dumps(dict(a, command=c))
            est = est_label(st, ep.info, w.table_z)
            row["est"] = est
            row["ndest_answer"] = json.dumps({"estimates": est, **a})
            c2, _ = nd_pt_command(row["step"], a["command"], st, ep.info, ep.head)
            if c2 is not None:
                if c2.get("point_2d") is None and c2.get("mode") == "point":
                    c2 = {k: v for k, v in c2.items() if k != "point_2d"}
                row["ndpt_answer"] = json.dumps({"estimates": est, **dict(a, command=c2)})
        return rep


def collect_episode(world, seed: int, task: str, variant: str, out_dir: str, p: float, max_perturb: int = 4,
                    stop_calls: int | None = 30, stop_motion_s: float | None = 120.0, style: str = "") -> dict:
    """= teach_l8.collect.collect_episode with a PtEpisode (same rng stream, same limits)."""
    rng = np.random.default_rng([int(seed), 8, LC.VARIANT_CODE.get(variant, 9)])
    coll = PtCollector(world, rng, p, max_perturb)
    ep = PtEpisode(world, coll, seed, task, out_dir, variant=variant, stop_calls=stop_calls,
                   stop_motion_s=stop_motion_s, allow_eef=True, save_v2=True, save_nd=True)
    coll.ep = ep
    res = ep.run()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "labels.jsonl"), "w") as f:
        for r in coll.rows:
            f.write(json.dumps(dict(r, seed=seed, task=task, variant=variant)) + "\n")
    meta = {"seed": seed, "task": task, "variant": variant, "p": p, "max_perturb": max_perturb, "style": style,
            "success": bool(res.get("success")), "end_reason": res.get("end_reason"), "n_calls": res["n_calls"],
            "n_rows": len(coll.rows), "n_perturb": coll.n_pert, "sim_t": res.get("sim_t"), "wall_s": res.get("wall_s"),
            "n_pt_labels": sum(r.get("pt_answer") is not None for r in coll.rows),
            "n_pt_unverified": sum(r.get("answer") is not None and r.get("pt_answer") is None for r in coll.rows)}
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    return meta
