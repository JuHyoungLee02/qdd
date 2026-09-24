"""R2 episode files (pure): the recorder (gen.py, Isaac) fills an in-memory episode; finalize() derives the text
state, labels_v2 decision labels, auxiliary geometry, §61 verification targets and the R4 rows and writes

  <folder>/ep<seed>.jsonl           one pool-format line per 30 Hz frame (k, t, text_state, pred, images, state.obs,
                                    decision flag + ds_id every 10 frames, task, instruction, verify) -- the R4 join
  <folder>/rows/ep<seed>.stageb.jsonl    R4 contract rows for every frame with a real action (k < K)
  <folder>/rows/ep<seed>.labels_v2.jsonl labels_v2 answers at the decision frames ({"seed","kind","k","labels_v2"})
  (in a subfolder: the loaders glob <folder>/ep*.jsonl for the frame lines)
  <folder>/ep<seed>.npz             30 Hz arrays (t, q, qd, tau, q_target, grip, obj poses, tcp, action, hold_n)
  <folder>/ep<seed>.meta.json       episode summary (written last = the done marker)
  <folder>/img/ep<seed>/f####_<cam>.jpg   (written by the recorder while running, JPEG q90, native resolution)

merge() concatenates the per-episode files of valid episodes into the loader's sibling files
<folder>.stageb.jsonl / <folder>.labels_v2.jsonl (stageb_data.stageb_path / stagea_data.labels_v2_path).
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

from .. import labels_v2 as L2
from ..sim import tasks as TK
from ..sim.snapshot import _jsonable, text_state
from . import rows as R
from .timing import DEC_EVERY, H_DEFAULT, HZ, is_decision

PHASE_IDS = {p: i for i, p in enumerate(("approach", "descend", "close", "lift", "carry", "place_descend", "open",
                                         "retreat", "done", "fail"))}
SCHEMA = "qdd.r2.episode/v1"


def _line(ep: dict, fr: dict, spec, split: str) -> dict:
    from ..sim.planner import PHASE_TIMEOUT_S
    tgt = spec.target
    txt = text_state(fr["t"], fr["phase"], fr["t_in_phase"], PHASE_TIMEOUT_S.get(fr["phase"], 60.0), fr["pred"],
                     fr["present"], fr["support"], bool(fr["pred"].get("gripper_open")),
                     bool(fr["pred"].get(f"holding({tgt})")), fr["arm_moving"], fr["changes"],
                     stages=TK.stages(spec), tgt=tgt)
    k = fr["k"]
    dec = is_decision(k)
    return {"seed": ep["seed"], "kind": ep["kind"], "task": ep["task"], "variant": ep["variant"],
            "instruction": spec.instruction, "split": split, "k": k, "t": round(fr["t"], 6),
            "t_nominal": round(k / HZ, 6), "ds_id": f"ds{k // DEC_EVERY}" if dec else None, "decision": dec,
            "phase": fr["phase"], "t_in_phase": round(fr["t_in_phase"], 4), "text_state": txt, "oracle": None,
            "pred": fr["pred"], "images": fr["images"],
            "state": {"t": round(fr["t"], 6), "present": list(fr["present"]),
                      "obs": {"pred": fr["pred"], "raw": fr["raw"], "near_hyst": fr.get("near_hyst", [])}}}


def finalize(ep: dict, folder: str, H: int = H_DEFAULT) -> dict:
    """Write the episode files (see module doc). ep: seed, kind, task, variant, split, frames [...], actions [K][8],
    hold_n [K], meta {...}. Returns the meta dict (also written, last)."""
    spec = TK.TASKS[TK.check_task(ep["task"])]
    tgt, place = spec.target, spec.place
    frames, acts = ep["frames"], np.asarray(ep["actions"], np.float32).reshape(-1, 8)
    K = len(frames) - 1
    if len(acts) != K:
        raise ValueError(f"{len(acts)} actions for {K + 1} frames (one per frame but the terminal one)")
    os.makedirs(f"{folder}/rows", exist_ok=True)
    base = f"{folder}/ep{ep['seed']}"
    rbase = f"{folder}/rows/ep{ep['seed']}"
    lines, rows, labs = [], [], []
    truths = []
    for fr in frames:
        ln = _line(ep, fr, spec, ep["split"])
        M, d = L2.delta(ln)
        tr = R.truth9(fr["pred"], tgt, place, fr["contact_open"])
        truths.append(tr)
        k = fr["k"]
        ver = {"truth": tr}
        if k >= DEC_EVERY and (is_decision(k) or k == K):  # the step started at the last decision frame before k
            k0 = (k - 1) // DEC_EVERY * DEC_EVERY
            ver["prev_step"] = R.verify_prev_step(frames[k0]["phase"], k0, tr)
        ln["verify"] = ver
        ln["motion_phase"], ln["goal_delta_m"] = M, [round(float(v), 5) for v in d]
        if ln["decision"]:
            labs.append({"seed": ep["seed"], "kind": ep["kind"], "k": k, "task": ep["task"],
                         "labels_v2": _jsonable(L2.labels(ln))})
        if k < K:
            rows.append(R.stageb_row(ep["seed"], ep["kind"], k, ep["task"], fr["phase"], fr["proprio"], acts, H,
                                     R.aux_row(ln["state"], tgt, place, d), verify=ver, decision=ln["decision"],
                                     variant=ep["variant"]))
        lines.append(ln)
    for path, items in ((f"{base}.jsonl", lines), (f"{rbase}.stageb.jsonl", rows), (f"{rbase}.labels_v2.jsonl", labs)):
        with open(path, "w", encoding="utf-8") as f:
            for x in items:
                f.write(json.dumps(_jsonable(x)) + "\n")
    st = ep["stream"]
    arrays = {k: np.asarray(v, np.float32) for k, v in st.items() if k not in ("obj_ids",)}
    arrays["obj_ids"] = np.array(st["obj_ids"])
    a_full = np.concatenate([acts, acts[-1:]], 0) if K > 0 else np.zeros((1, 8), np.float32)
    arrays.update(action=a_full, action_real=np.array([1] * K + [0], np.int8),
                  hold_n=np.array(list(ep["hold_n"]) + [0], np.int8),
                  phase_id=np.array([PHASE_IDS.get(fr["phase"], -1) for fr in frames], np.int8),
                  truth=np.array([[-1 if tr[n] is None else int(bool(tr[n])) for n in R_TRUTH] for tr in truths], np.int8))
    np.savez_compressed(f"{base}.npz", **arrays)
    meta = dict(ep["meta"], schema=SCHEMA, seed=ep["seed"], kind=ep["kind"], task=ep["task"], variant=ep["variant"],
                split=ep["split"], instruction=spec.instruction, target=tgt, place=place, hz=HZ, H=H,
                n_frames=K + 1, n_actions=K, n_rows=len(rows), n_decisions=len(labs), truth_names=list(R_TRUTH))
    with open(f"{base}.meta.json", "w", encoding="utf-8") as f:
        json.dump(_jsonable(meta), f, indent=1)
    return meta


R_TRUTH = ("on_tp", "contact_tp", "lifted_t", "near_tp", "above_tp", "gripper_open", "holding_t", "lifted_holding",
           "contact_stall")


def merge(folder: str, include_invalid: bool = False) -> dict:
    """<folder>.stageb.jsonl and <folder>.labels_v2.jsonl from the per-episode files of this folder (valid
    episodes only unless include_invalid). Returns counts."""
    eps, n_rows, n_lab, skipped = 0, 0, 0, []
    root = folder.rstrip("/\\")
    with open(root + ".stageb.jsonl", "w", encoding="utf-8") as fr, \
            open(root + ".labels_v2.jsonl", "w", encoding="utf-8") as fl:
        for mp in sorted(glob.glob(f"{root}/ep*.meta.json"), key=lambda p: int(os.path.basename(p)[2:-10])):
            meta = json.load(open(mp, encoding="utf-8"))
            if not include_invalid and not meta.get("valid_for_training"):
                skipped.append(meta["seed"])
                continue
            base = f"{root}/rows/ep{meta['seed']}"
            for src, dst in ((".stageb.jsonl", fr), (".labels_v2.jsonl", fl)):
                with open(base + src, encoding="utf-8") as f:
                    for x in f:
                        dst.write(x)
                        if src == ".stageb.jsonl":
                            n_rows += 1
                        else:
                            n_lab += 1
            eps += 1
    return {"folder": root, "episodes": eps, "rows": n_rows, "labels": n_lab, "skipped_invalid": skipped}
