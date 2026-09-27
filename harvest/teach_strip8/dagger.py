"""boost2 DAgger collection (docs/stage3/prereg_boost2.md): the L8-D collection path (teach_l8d.collect: XCollector
inside a PtEpisode that saves every request / image / depth and the truth labels) with the behaviour policy replaced
by the LEARNER: at each call the collector first labels the state with the truth (clean, no perturbation), then asks
the served B-D model with the d-min request of the same state (min_format.d_text of the saved v2 request + ring-only
head image + wrist image) and returns the model's answer to execute (point + depth converter). An invalid or failed
model answer executes the truth command instead (counted). Rows: exec_kind 'model' / 'truth_fallback'; the next row's
prev_kind is 'dagger' when the executed command differed from the truth (recovery states get the L8 repeat weight)."""
from __future__ import annotations

import json
import os

import numpy as np

from ..astra_motion.truth import Rep
from ..teach_l8d.collect import XCollector

LEARNER_KIND = "dagger"


class DaggerCollector(XCollector):
    name = "l8x_dagger"

    def __init__(self, world, rng, model, validate):
        super().__init__(world, rng, 0.0, 0)
        self.model, self.validate = model, validate
        self.n_model = self.n_fallback = 0

    def ask(self, text, images, meta):
        truth = super().ask(text, images, meta)  # appends the labelled row; p = 0 -> the truth command
        row = self.rows[-1]
        if row.get("answer") is None:  # tipped: stop as the truth does
            return truth
        from ..teach_pt.min_format import d_text
        ep = self.ep
        req = d_text(ep.v2_text)
        ims = [(images[0][0], ep.ring_png), images[1]]
        if getattr(self.model, "ep", 0) is None:  # truth-backed learners (tests) need the episode
            self.model.ep = ep
        rep = self.model.ask(req, ims, dict(meta, dagger=True))
        parsed, err = (None, ["api"]) if (rep.error and not rep.text) else self.validate(rep.text)
        tcmd = json.loads(truth.text)["command"]
        if parsed is None:
            self.n_fallback += 1
            row["exec_kind"] = "truth_fallback"
            row["learner_errors"] = err[:4]
            self.prev_kind = "clean"
            return truth
        self.n_model += 1
        row["exec_kind"] = "model"
        row["learner_command"] = parsed["command"]
        same = _same(parsed["command"], tcmd)
        self.prev_kind = "clean" if same else LEARNER_KIND
        self.prev_cmd = None  # learner targets are not truth targets: no 'stuck' comparison
        return Rep(rep.text)


def _same(a: dict, b: dict) -> bool:
    return a.get("mode") == b.get("mode") and a.get("gripper") == b.get("gripper") and a.get("height") == b.get("height")


def collect_episode(world, seed: int, task: str, variant: str, split: str, out_dir: str, model,
                    stop_calls: int = 20, stop_motion_s: float = 60.0) -> dict:
    """= teach_l8d.collect.collect_episode (single-step tasks) with the DaggerCollector."""
    from ..astra_solo import pt_schema as PS
    from ..astra_solo.pt_episode import PtEpisode
    from ..teach_l8 import collect as LC
    from ..teach_l8d.collect import scene_record
    rng = np.random.default_rng([int(seed), 8, LC.VARIANT_CODE.get(variant, 9)])
    coll = DaggerCollector(world, rng, model, lambda t: PS.validate(t, allow_eef=True))
    ep = PtEpisode(world, coll, seed, task, out_dir, variant=variant, stop_calls=stop_calls,
                   stop_motion_s=stop_motion_s, allow_eef=True, save_v2=True, save_nd=True)
    coll.ep = ep
    res = ep.run()
    os.makedirs(out_dir, exist_ok=True)
    scene = scene_record(world, seed, task, variant, split, "dagger")
    with open(os.path.join(out_dir, "scene.json"), "w") as f:
        json.dump(scene, f)
    with open(os.path.join(out_dir, "labels.jsonl"), "w") as f:
        for r in coll.rows:
            f.write(json.dumps(dict(r, seed=seed, task=task, variant=variant, table_z=scene["table_z"])) + "\n")
    meta = {"seed": seed, "split": split, "task": task, "variant": variant, "table_z": scene["table_z"],
            "success": bool(res.get("success")), "end_reason": res.get("end_reason"), "n_calls": res["n_calls"],
            "n_rows": len(coll.rows), "n_model": coll.n_model, "n_fallback": coll.n_fallback,
            "n_labelled": sum(r.get("answer") is not None and r.get("drop") is None for r in coll.rows),
            "n_pt_labels": sum(r.get("pt_answer") is not None for r in coll.rows), "style": "dagger"}
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    return meta
