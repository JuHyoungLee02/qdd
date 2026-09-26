"""E-TEACH-L8 collection (prereg §3.2): the runtime astra-solo Episode (prompt astra-solo@v2, overlay, executor,
measured history, prompt limits 40 calls / 180 s) is driven by the Collector 'model': at every call it labels the
state with the truth command (labels.py), then returns the command to EXECUTE (behavior.py: the truth, or a
perturbation). The Episode saves each request (prompt.txt + the two PNGs, exactly what a model receives); the
collector writes labels.jsonl next to it (one row per call: label answer, step / phase / status, the kind executed
before (prev_kind) and at this call (exec_kind), ground truth for the perception questions, executor target, drawn
overlay elements, drop flag). Seeds: TRAIN = R2_TRAIN 10000-59999 (datagen.gen, canon §66), DEV 0-19 evaluation
only (mug_tray). Pure except the Isaac world (run_collect.py)."""
from __future__ import annotations

import json
import os

import numpy as np

from ..astra_motion.geometry import pixel_of
from ..astra_motion.truth import Rep
from ..astra_solo.episode import Episode
from . import behavior as B
from . import labels as L

TRAIN_SEEDS = range(10000, 60000)
DEV_SEEDS = range(0, 20)
PREV_KINDS = ("start", "clean") + tuple(sorted(set(B.APPROACH_KINDS) | set(B.CARRY_KINDS)))
VARIANT_CODE = {"standard": 0, "dr": 1}


def check_seed(seed: int, split: str) -> int:
    s = int(seed)
    if split == "dev" and s in DEV_SEEDS:
        return s
    if split == "train" and s in TRAIN_SEEDS:
        return s
    raise ValueError(f"seed {s} is not a {split} seed (train {TRAIN_SEEDS.start}-{TRAIN_SEEDS.stop - 1}, "
                     f"dev {DEV_SEEDS.start}-{DEV_SEEDS.stop - 1})")


def task_of(seed: int, split: str) -> str:
    if split == "dev":
        return "mug_tray"
    return ("mug_tray", "mug_tray", "mug_tray", "bottle_tray", "mug_marker")[seed % 5]


def visible(cams: dict, p) -> bool:
    """The object centre projects inside the head or the right wrist image (prereg §3.3 drop rule)."""
    return any(pixel_of(cams[k], p)[2] for k in ("head", "wrist") if k in cams)


def _l(v):
    return [round(float(x), 4) for x in np.asarray(v, float)]


class Collector:
    name = "l8_behavior"

    def __init__(self, world, rng, p: float, max_perturb: int):
        self.w, self.rng, self.p, self.max_perturb = world, rng, p, max_perturb
        self.ep = None
        self.rows: list = []
        self.prev_kind, self.prev_failed, self.n_pert, self.prev_cmd = "start", False, 0, None

    def ask(self, text, images, meta):
        ep, w = self.ep, self.w
        st, info = w.status(), ep.info
        last = ep.history[-1] if ep.history else ""
        lab = L.label(st, info, w.table_z, w.w_open, first=not ep.history, last_line=last,
                      prev_failed=self.prev_failed)
        cams = w.last_obs.cams if getattr(w, "last_obs", None) is not None else {}
        tgt = np.asarray(st["obj"][info["tgt"]], float)
        drop = "tipped" if lab is None else ("not_visible" if cams and not visible(cams, tgt) else None)
        if drop is None and L.stuck(last, self.prev_cmd, lab["command"]):
            drop = "stuck"
        row = {"call": meta["call"], "site": meta["site"], "prev_kind": self.prev_kind, "drop": drop,
               "gt": {"tgt": _l(tgt), "place": _l(st["obj"][info["place"]]), "tcp": _l(st["tcp"]),
                      "grip_w": round(float(st["grip_w"]), 4),
                      "others": {k: _l(v) for k, v in st["obj"].items() if k not in (info["tgt"], info["place"])}},
               "ex_target": _l(ep.ex.target), "drawn": list(getattr(ep, "drawn", [])),
               "tgt": info["tgt"], "place": info["place"]}
        if lab is None:
            row.update(step="tipped", phase="tipped", status=None, answer=None, exec_kind="stop")
            self.rows.append(row)
            return Rep(json.dumps({"assessment": _stub(), "command": {"mode": "stop"}, "reason": "tipped"}))
        row.update(step=lab["step"], phase=lab["phase"], status=lab["status"], answer=lab["answer"])
        c = B.Ctx(state=st, info=info, table_z=w.table_z, step=lab["step"], label_cmd=lab["command"])
        cmd, kind = B.choose(self.rng, c, self.p if self.n_pert < self.max_perturb else 0.0)
        self.n_pert += kind != "clean"
        row["exec_kind"] = kind
        self.rows.append(row)
        self.prev_kind, self.prev_failed, self.prev_cmd = kind, lab["status"] == "failed", cmd
        a = json.loads(lab["answer"])
        return Rep(json.dumps({"assessment": a["assessment"], "command": cmd, "reason": kind}))


def _stub():
    return {"task_progress": {"verified_completed": [], "currently_attempting": "stop", "remaining": []},
            "execution_status": "failed", "evidence": "target tipped", "evidence_view": "both", "confidence": "high"}


def collect_episode(world, seed: int, task: str, variant: str, out_dir: str, p: float, max_perturb: int = 4,
                    stop_calls: int | None = 30, stop_motion_s: float | None = 120.0, style: str = "") -> dict:
    rng = np.random.default_rng([int(seed), 8, VARIANT_CODE.get(variant, 9)])
    coll = Collector(world, rng, p, max_perturb)
    ep = Episode(world, coll, seed, task, out_dir, variant=variant, stop_calls=stop_calls,
                 stop_motion_s=stop_motion_s)
    coll.ep = ep
    res = ep.run()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "labels.jsonl"), "w") as f:
        for r in coll.rows:
            f.write(json.dumps(dict(r, seed=seed, task=task, variant=variant)) + "\n")
    meta = {"seed": seed, "task": task, "variant": variant, "p": p, "max_perturb": max_perturb, "style": style,
            "success": bool(res.get("success")), "end_reason": res.get("end_reason"), "n_calls": res["n_calls"],
            "n_rows": len(coll.rows), "n_perturb": coll.n_pert, "sim_t": res.get("sim_t"), "wall_s": res.get("wall_s")}
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f)
    return meta
