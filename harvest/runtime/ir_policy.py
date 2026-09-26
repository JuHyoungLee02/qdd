"""`OursPolicy`: the thin Inspect Robots adapter over OursRuntime (P2, canon §42, D23 §2 and §6).

act() returns a one-action chunk (DefaultController(replan_interval=1)); policy.config = RuntimeConfig (EvalSpec.
policy_config); on_trial_end writes the per-trial sidecar JSONL (calls with votes / option_key / epochs, decision
steps with M4 status and (b) outcomes, Astra heartbeats, skill events) + sampled frames, and puts the paths and the
summary into record.metadata (-> SceneResult.trial_metadata).
"""
from __future__ import annotations

import json
import os
from dataclasses import replace

import numpy as np


class OursPolicy:
    def __init__(self, runtime, name: str, checkpoint: str | None = None):
        from inspect_robots import ActionSemantics, Box, ObservationSpace, PolicyInfo
        self.rt, self.config = runtime, runtime.cfg
        self.info = PolicyInfo(name=name, action_space=Box(shape=(8,), semantics=ActionSemantics(
            control_mode="joint_pos", gripper="continuous")),
            observation_space=ObservationSpace(state_keys=frozenset({"joint_pos"})), control_hz=100.0,
            checkpoint=checkpoint)
        self.low, self.high = np.full(8, -np.inf), np.full(8, np.inf)

    def bind(self, embodiment_info) -> None:
        box = embodiment_info.action_space
        self.info = replace(self.info, action_space=box)
        self.low, self.high = np.asarray(box.low, float), np.asarray(box.high, float)

    def reset(self, scene) -> None:
        self.rt.reset()
        self.scene_id = scene.id

    def act(self, observation):
        from inspect_robots import Action, ActionChunk
        x = observation.extra
        obs = {"sim_time": x["sim_time"], "joint_pos": observation.state["joint_pos"], "images": observation.images,
               "m1": x["m1"], "kin": x["kin"], "table_z": x["table_z"], "low": self.low, "high": self.high,
               "cams": x.get("cams")}
        a, meta = self.rt.act(obs)
        return ActionChunk(actions=[Action(data=np.asarray(a, float), meta=meta)], control_hz=100.0)

    def transcript(self):
        return {"astra": [dict(a) for a in self.rt.astra_log]}

    def on_trial_end(self, record, log_dir: str, run_id: str) -> None:
        rt = self.rt
        d = os.path.join(log_dir, "ours", run_id)
        os.makedirs(d, exist_ok=True)
        stem = f"{record.scene_id}-e{record.epoch}"
        side = os.path.join(d, stem + ".jsonl")
        with open(side, "w", encoding="utf-8") as f:
            for kind, rows in (("call", rt.calls), ("step", rt.slots_log), ("astra", rt.astra_log),
                               ("event", rt.events), ("m4", rt.ledger.log), ("chunk", rt.chunk_log),
                               ("measure", getattr(rt, "measure_log", [])),
                               ("couple", _couple_rows(rt))):
                for r in rows:
                    f.write(json.dumps({"type": kind, **_jsonable(r)}) + "\n")
        nb = write_blobs(d, getattr(rt, "blobs", {}))  # raw requests / responses / Astra images (canon §77)
        fdir = os.path.join(d, stem + "_frames")
        os.makedirs(fdir, exist_ok=True)
        if rt.sampled:
            from PIL import Image
        for t, ph, name, img in rt.sampled:
            Image.fromarray(img).save(os.path.join(fdir, f"t{t:06.2f}_{ph}_{name}.jpg"), quality=90)
        s = rt.summary()
        last = record.steps[-1].result.info if record.steps else {}
        s.update(sim_time_end=last.get("sim_time"), rtf_env=last.get("rtf"), env_success=last.get("success"),
                 n_steps=len(record.steps))
        s.update(blobs_dir=os.path.join(d, "blobs"), blobs_new=nb)
        record.metadata.update({"ours_sidecar": side, "ours_frames": fdir, "ours_summary": s, "seed": record.seed,
                                "ours_blobs": os.path.join(d, "blobs")})
        with open(os.path.join(d, stem + "_summary.json"), "w", encoding="utf-8") as f:
            json.dump(_jsonable(s), f, indent=1)


def _couple_rows(rt) -> list:
    """The coupling driver's log (spec 2026-09-26 §16). Its rows carry their own "type" (send / answer / timeout /
    adherence / ...), which would overwrite the sidecar type "couple": it is kept as "couple_kind"."""
    drv = getattr(rt, "driver", None)
    if drv is None:
        return []
    return [{"couple_kind": r.get("type"), **{k: v for k, v in r.items() if k != "type"}} for r in drv.log]


def write_blobs(d: str, blobs: dict) -> int:
    """Content-addressed files <d>/blobs/<sha256>.<ext> (shared by the trials of a run; an existing file is the same
    content, so it is not rewritten). Returns the number of new files."""
    bd = os.path.join(d, "blobs")
    os.makedirs(bd, exist_ok=True)
    n = 0
    for h, (ext, b) in blobs.items():
        p = os.path.join(bd, f"{h}.{ext}")
        if os.path.exists(p):
            continue
        with open(p + ".tmp", "wb") as f:
            f.write(b)
        os.replace(p + ".tmp", p)
        n += 1
    return n


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating, np.integer, np.bool_)):
        return x.item()
    return x
