"""E-PT dataset (prereg_pt.md §3): collected E-PT episodes -> JSONL rows per ARM in the teach_l8 row format (train.py
and evaluate.py read them unchanged). Every arm uses the SAME states (the L8 behaviour collection); only the request
(prompt file + head image) and the answer differ:
  xyz     prompt_v2.txt + v2 overlay head | L8 xyz answer            (= E-TEACH-L8's input; its adapter is reused)
  pt      prompt.txt    + v2 overlay head | pt answer (depth-verified pixel + height intent)
  nd-xyz  prompt_nd-xyz@v1.txt + ring-only head | L8 xyz answer
  nd-est  prompt_nd-est@v1.txt + ring-only head | estimates + L8 xyz answer
  nd-pt   prompt_nd-pt@v1.txt  + ring-only head | estimates + point (top-centre pixel, top_z)
Control rows missing a label for an arm (pt: no verified pixel; nd-pt: top centre outside the image) are dropped for
that arm (counted). repeats = teach_l8.dataset.repeat_of. aux = one perception QA per control row on the arm's head
image: pt -> pointing ({"point_2d"}, verified object pixel or the TCP ring); xyz / nd-* -> robot-frame (x, y) of an
object's base centre or the TCP ({"xy"}, like L8's aux; no grid mentioned for nd-*).
Offline fields on every row: depth / cams paths, pt_state (holding, grip offset, plane), gt, pixels, est."""
from __future__ import annotations

import json
import os
from collections import Counter

import numpy as np

from ..astra_motion.prompts import OBJ_NAME
from ..teach_l8.dataset import IMAGE_FILES, _on_table, episode_dirs, repeat_of

ARMS = ("xyz", "pt", "nd-xyz", "nd-est", "nd-pt")
PROMPT_FILE = {"xyz": "prompt_v2.txt", "pt": "prompt.txt", "nd-xyz": "prompt_nd-xyz@v1.txt",
               "nd-est": "prompt_nd-est@v1.txt", "nd-pt": "prompt_nd-pt@v1.txt"}
HEAD_FILE = {"xyz": IMAGE_FILES[0], "pt": IMAGE_FILES[0], "nd-xyz": "img1_head_ring.png",
             "nd-est": "img1_head_ring.png", "nd-pt": "img1_head_ring.png"}
ANSWER_KEY = {"xyz": "answer", "pt": "pt_answer", "nd-xyz": "answer", "nd-est": "ndest_answer",
              "nd-pt": "ndpt_answer"}
PT_ASK = {"tgt": "Point to the {name} in image 1.", "place": "Point to the {name} in image 1.",
          "other": "Point to the {name} in image 1.",
          "tcp": "Point to the gripper's TCP (the white ring drawn on the robot's right gripper) in image 1."}
PT_HEAD = "Image 1 is the robot's head camera (a white grid is drawn on the table).\n"
PT_TAIL = ('\nReturn JSON only: {"point_2d": [x, y]} with x, y on a 0-1000 scale of image 1 (x from the left edge, y '
           'from the top edge).')
XY_HEAD = {"xyz": ("Image 1 is the robot's head camera. White grid lines lie on the table surface every 5 cm, "
                   "labelled with robot-frame metres (x forward, away from the robot; y to the robot's left).\n"),
           "nd": ("Image 1 is the robot's head camera (the white ring is the gripper's TCP). Robot frame: x forward, "
                  "away from the robot; y to the robot's left; metres.\n")}
XY_ASK = {"tgt": "What is the robot-frame (x, y) of the centre of the base of the {name} (where it meets the table)?",
          "place": "What is the robot-frame (x, y) of the centre of the {name}?",
          "other": "What is the robot-frame (x, y) of the centre of the base of the {name}?",
          "tcp": "What is the robot-frame (x, y) of the gripper's TCP (the white ring)?"}
XY_TAIL = '\nReturn JSON only: {"xy": [x, y]} in metres.'


def _check(seed: int, split: str):
    from ..teach_l8.collect import DEV_SEEDS, TRAIN_SEEDS
    from .collect import OOD_D_SEEDS
    ok = {"train": TRAIN_SEEDS, "dev": DEV_SEEDS, "ood_d": OOD_D_SEEDS, "ood_h": DEV_SEEDS}[split]
    if seed not in ok:
        raise ValueError(f"seed {seed} is not a {split} seed")


def load_rows(ep_dir: str, split: str) -> list:
    rows = []
    vdir = os.path.basename(os.path.dirname(ep_dir))
    for line in open(os.path.join(ep_dir, "labels.jsonl")):
        x = json.loads(line)
        _check(x["seed"], split)
        if x["drop"] is not None:
            continue
        c = os.path.join(ep_dir, "calls", f"c{x['call']:03d}")
        rows.append(dict(x, id=f"{vdir}_{x['task']}_s{x['seed']}_c{x['call']:03d}",
                         episode=os.path.basename(ep_dir) + "_" + vdir, call_dir=c, vdir=vdir,
                         depth_path=os.path.join(c, "head_depth.npz"), cams_path=os.path.join(c, "cams.json")))
    return rows


def arm_row(r: dict, arm: str):
    ans = r.get(ANSWER_KEY[arm])
    if ans is None:
        return None
    c = r["call_dir"]
    return dict(r, kind="control", arm=arm, prompt_path=os.path.join(c, PROMPT_FILE[arm]),
                images=[os.path.join(c, HEAD_FILE[arm]), os.path.join(c, IMAGE_FILES[1])], answer=ans,
                xyz_answer=r["answer"])


def _objects(r):
    objs = {r["tgt"]: ("tgt", r["gt"]["tgt"]), r["place"]: ("place", r["gt"]["place"])}
    for k, v in sorted(r["gt"]["others"].items()):
        if k in OBJ_NAME and _on_table(v):
            objs[k] = ("other", v)
    return objs


def aux_pixels(r: dict) -> dict:
    """Depth-verified pointing pixels of the objects on this call's head image (pt_truth.label_pixel)."""
    from ..astra_motion.geometry import Cam
    from ..astra_solo.pt_truth import label_pixel
    cam = Cam.from_json(json.load(open(r["cams_path"]))["head"])
    depth = np.load(r["depth_path"])["depth"]
    return {k: label_pixel(cam, depth, r["pt_state"]["plane"], c, k)[0] for k, (_, c) in _objects(r).items()}


def aux_for(r: dict, arm: str, rng):
    opts = []
    if arm == "pt":
        px = aux_pixels(r)
        for k, (kind, _) in _objects(r).items():
            if px.get(k) is not None:
                opts.append((kind, k, px[k]))
        if "tcp" in r.get("drawn", []) and r["pixels"].get("tcp") is not None:
            opts.append(("tcp", None, r["pixels"]["tcp"]))
    else:
        for k, (kind, c) in _objects(r).items():
            opts.append((kind, k, c))
        if r["pixels"].get("tcp") is not None:
            opts.append(("tcp", None, r["gt"]["tcp"]))
    if not opts:
        return None
    kinds = sorted({o[0] for o in opts})  # kind uniform, then an object of that kind
    kind = kinds[int(rng.integers(len(kinds)))]
    cand = [o for o in opts if o[0] == kind]
    _, key, v = cand[int(rng.integers(len(cand)))]
    name = OBJ_NAME.get(key, "")
    if arm == "pt":
        q, a = PT_HEAD + PT_ASK[kind].format(name=name) + PT_TAIL, {"point_2d": [int(v[0]), int(v[1])]}
    else:
        q = XY_HEAD["xyz" if arm == "xyz" else "nd"] + XY_ASK[kind].format(name=name) + XY_TAIL
        a = {"xy": [round(float(v[0]), 3), round(float(v[1]), 3)]}
    head = os.path.join(r["call_dir"], HEAD_FILE[arm])
    return {"id": r["id"] + f"_aux_{kind}", "kind": "aux", "arm": arm, "aux_kind": kind, "prompt": q,
            "images": [head], "answer": json.dumps(a), "seed": r["seed"], "task": r["task"], "variant": r["variant"],
            "episode": r["episode"], "cams_path": r["cams_path"]}


def build(root: str, out_dir: str, split: str, arms=ARMS, seed: int = 0, repeats: bool = True, aux: bool = True) -> dict:
    base = [r for d in episode_dirs(root) for r in load_rows(d, split)]
    os.makedirs(out_dir, exist_ok=True)
    counts = {"episodes": len(episode_dirs(root)), "rows_labelled": len(base), "arms": {}}
    for arm in arms:
        rng = np.random.default_rng([seed, ARMS.index(arm)])
        ctrl = [x for x in (arm_row(r, arm) for r in base) if x is not None]
        rows = []
        for r in ctrl:
            rows += [r] * (repeat_of(r) if repeats else 1)
        auxr = [a for a in (aux_for(r, arm, rng) for r in ctrl) if a is not None] if aux else []
        with open(os.path.join(out_dir, f"{split}_{arm}.jsonl"), "w") as f:
            for r in rows + auxr:
                f.write(json.dumps(r) + "\n")
        counts["arms"][arm] = {"control_unique": len(ctrl), "dropped": len(base) - len(ctrl),
                               "control_rows": len(rows), "aux_rows": len(auxr), "total": len(rows) + len(auxr),
                               "by_step": dict(Counter(r["step"] for r in ctrl)),
                               "by_aux_kind": dict(Counter(r["aux_kind"] for r in auxr)),
                               "dropped_by_step": dict(Counter(r["step"] for r in base
                                                               if r.get(ANSWER_KEY[arm]) is None))}
    with open(os.path.join(out_dir, f"{split}.counts.json"), "w") as f:
        json.dump(counts, f, indent=1)
    return counts
