"""E-TEACH-L8 dataset (prereg §3.4): collected episodes -> JSONL of training / evaluation samples.

control  the exact runtime request (prompt.txt + head overlay PNG + right wrist PNG, content order of
         astra_motion.models.LocalVLM) -> the truth label answer (astra-solo@v2 JSON).
         repeat_of: 1 + 1 for approach / descend steps (where the zero-shot errors were) + 1 for recovery states
         (the previous executed command was a perturbation).
aux      perception QA on the same head image (the runtime schema is untouched): robot-frame (x, y) of the target's
         base centre, the place object's centre, another object's base centre, or the drop-line dot under the TCP
         (only when drawn). One question per labelled call, kind drawn uniformly from those available. Ground truth
         from the simulator.
Dropped calls (tipped target, target outside both images) are not used. Split guard: split 'train' refuses DEV
seeds, split 'dev' refuses non-DEV seeds."""
from __future__ import annotations

import glob
import json
import os
from collections import Counter

import numpy as np

from ..astra_motion.prompts import OBJ_NAME
from .collect import DEV_SEEDS, TRAIN_SEEDS

IMAGE_FILES = ("img1_head_camera.png", "img2_right_wrist_camera.png")
IMAGE_LABELS = ("head camera", "right wrist camera")  # = astra_solo.prompts.IMAGE_LABELS
UP_STEPS = ("above_target", "descend_close")
TABLE_BOX = ((0.15, 0.80), (-0.70, 0.40))
AUX_HEAD = ("Image 1 is the robot's head camera. White grid lines lie on the table surface every 5 cm, labelled "
            "with robot-frame metres (x forward, away from the robot; y to the robot's left).\n")
AUX_ASK = {
    "tgt": "What is the robot-frame (x, y) of the centre of the base of the {name} (where it meets the table)?",
    "place": "What is the robot-frame (x, y) of the centre of the {name}?",
    "other": "What is the robot-frame (x, y) of the centre of the base of the {name}?",
    "drop": ("A white dotted line runs from the gripper's TCP ring straight down to a white dot on the table. What is "
             "the robot-frame (x, y) of that dot?"),
}
AUX_TAIL = '\nReturn JSON only: {"xy": [x, y]} in metres.'


def user_content(text: str, n_images: int) -> list:
    """Chat content of one request, in the LocalVLM order (text, then 'Image k: label' + image per image)."""
    out = [{"type": "text", "text": text}]
    for i in range(n_images):
        out.append({"type": "text", "text": f"Image {i + 1}: {IMAGE_LABELS[i]}"})
        out.append({"type": "image"})
    return out


def episode_dirs(root: str) -> list:
    return sorted(os.path.dirname(p) for p in glob.glob(os.path.join(root, "**", "labels.jsonl"), recursive=True))


def repeat_of(r: dict) -> int:
    return 1 + (r["step"] in UP_STEPS) + (r["prev_kind"] not in ("start", "clean"))


def dedup(rows: list) -> list:
    seen, out = set(), []
    for r in rows:
        if r["id"] not in seen:
            seen.add(r["id"])
            out.append(r)
    return out


def _on_table(p) -> bool:
    return TABLE_BOX[0][0] <= p[0] <= TABLE_BOX[0][1] and TABLE_BOX[1][0] <= p[1] <= TABLE_BOX[1][1]


def aux_for(r: dict, rng) -> dict:
    opts = [("tgt", r["tgt"], r["gt"]["tgt"]), ("place", r["place"], r["gt"]["place"])]
    others = [(k, v) for k, v in sorted(r["gt"]["others"].items()) if k in OBJ_NAME and _on_table(v)]
    if others:
        k, v = others[int(rng.integers(len(others)))]
        opts.append(("other", k, v))
    if "drop" in r.get("drawn", []):
        opts.append(("drop", None, r["gt"]["tcp"]))
    kind, obj, xy = opts[int(rng.integers(len(opts)))]
    q = AUX_HEAD + AUX_ASK[kind].format(name=OBJ_NAME.get(obj, "")) + AUX_TAIL
    return {"id": r["id"] + f"_aux_{kind}", "kind": "aux", "aux_kind": kind, "prompt": q, "images": r["images"][:1],
            "answer": json.dumps({"xy": [round(float(xy[0]), 3), round(float(xy[1]), 3)]}), "seed": r["seed"],
            "task": r["task"], "variant": r["variant"], "episode": r["episode"]}


def load_control(ep_dir: str, split: str) -> list:
    rows = []
    for line in open(os.path.join(ep_dir, "labels.jsonl")):
        x = json.loads(line)
        ok = DEV_SEEDS if split == "dev" else TRAIN_SEEDS
        if x["seed"] not in ok:
            raise ValueError(f"seed {x['seed']} in {ep_dir} is not a {split} seed")
        if x["drop"] is not None:
            continue
        c = os.path.join(ep_dir, "calls", f"c{x['call']:03d}")
        rows.append(dict(x, id=f"{x['variant']}_{x['task']}_s{x['seed']}_c{x['call']:03d}", kind="control",
                         episode=os.path.basename(ep_dir) + "_" + x["variant"],
                         prompt_path=os.path.join(c, "prompt.txt"), images=[os.path.join(c, f) for f in IMAGE_FILES]))
    return rows


def build(root: str, out: str, split: str, seed: int = 0, repeats: bool = True, aux: bool = True) -> dict:
    rng = np.random.default_rng(seed)
    ctrl = [r for d in episode_dirs(root) for r in load_control(d, split)]
    rows = []
    for r in ctrl:
        rows += [r] * (repeat_of(r) if repeats else 1)
    auxr = [aux_for(r, rng) for r in ctrl] if aux else []
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w") as f:
        for r in rows + auxr:
            f.write(json.dumps(r) + "\n")
    counts = {"episodes": len(episode_dirs(root)), "control_unique": len(ctrl), "control_rows": len(rows),
              "aux_rows": len(auxr), "by_step": dict(Counter(r["step"] for r in ctrl)),
              "by_phase": dict(Counter(r["phase"] for r in ctrl)),
              "by_prev_kind": dict(Counter(r["prev_kind"] for r in ctrl)),
              "by_phase_x_state": dict(Counter(f"{r['phase']}|{'recovery' if r['prev_kind'] not in ('start', 'clean') else 'on_path'}"
                                               for r in ctrl)),
              "by_task": dict(Counter(r["task"] for r in ctrl)), "by_variant": dict(Counter(r["variant"] for r in ctrl)),
              "by_aux_kind": dict(Counter(r["aux_kind"] for r in auxr)),
              "rows_by_step_weighted": dict(Counter(r["step"] for r in rows))}
    with open(out + ".counts.json", "w") as f:
        json.dump(counts, f, indent=1)
    return counts
