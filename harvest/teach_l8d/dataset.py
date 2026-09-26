"""L8-D dataset (prereg_l8d.md §3): collected L8-D episodes -> JSONL rows in the teach_l8 / teach_pt row format
(train.py / evaluate.py read them unchanged), in a format chosen at build time from the SAME saved states:
  v2      prompt_v2.txt + grid overlay head (hand-given info on: table height, sizes, recipes, grid) = L8's input
  nd-xyz  PT-ND nd-xyz@v1 request + ring-only head (no grid, no table height)
  nd-est  nd-est@v1 (estimates first), nd-pt (estimates + point), pt (point request, depth resolver)
  s-min   E-STRIP8 minimal request (strip.minimal of the v2 request: no table line, grid, sizes, recipes) + ring head
Labels, repeats (teach_l8.dataset.repeat_of) and aux perception QA are those of teach_pt.dataset (s-min uses the
nd-xyz aux rows). tags=True prefixes every request with 'source: qdd_sim/ffw_sg2' / 'frame: base_ffw_sg2' (the open8
convention, tools/xemb/fmt.py); answers never carry a frame key. Every row gets `scene` (table_z, lift, variant,
task, n_distractors, distractor names, height / distractor bins). Split guard: train = TRAIN seeds 30000-34999 with
variant standard / drx only; gate = GATE seeds; ood_* = that OOD set's seeds only."""
from __future__ import annotations

import json
import os
from collections import Counter

import numpy as np

from ..teach_l8.dataset import episode_dirs, repeat_of
from ..teach_pt import dataset as PD
from . import spec as SP

FORMATS = ("v2", "nd-xyz", "nd-est", "nd-pt", "pt", "s-min")
PT_ARM = {"v2": "xyz", "nd-xyz": "nd-xyz", "nd-est": "nd-est", "nd-pt": "nd-pt", "pt": "pt", "s-min": "nd-xyz"}
TAG_LINES = "source: qdd_sim/ffw_sg2\nframe: base_ffw_sg2\n"
TRAIN_VARIANTS = ("standard", "drx")


def check_row(r: dict, split: str) -> None:
    s, v = int(r["seed"]), r["variant"]
    if split == "train":
        if s not in SP.TRAIN_SEEDS or v not in TRAIN_VARIANTS:
            raise ValueError(f"train row refused: seed {s} / variant {v} (TRAIN 30000-34999, standard / drx)")
        if r.get("task") in SP.OOD_O_TASKS + SP.OOD_T_TASKS:
            raise ValueError(f"train row refused: task {r['task']} is held out (OOD-O / OOD-T)")
    elif split == "gate":
        if s not in SP.GATE_SEEDS:
            raise ValueError(f"gate row refused: seed {s}")
    elif split in SP.OOD_SETS:
        if s not in SP.OOD_SETS[split]:
            raise ValueError(f"{split} row refused: seed {s}")
    else:
        raise ValueError(f"split {split!r}")


def scene_of(ep_dir: str) -> dict:
    sc = json.load(open(os.path.join(ep_dir, "scene.json")))
    d = sc["distractors"]
    return {"table_z": sc["table_z"], "lift": sc.get("lift"), "variant": sc["variant"], "task": sc["task"],
            "n_distractors": d["n"], "distractors": d["layout_objects"] + d["pool_distractors"],
            "height_bin": SP.height_bin(sc["table_z"]), "dist_bin": SP.dist_bin(d["n"]), "ws": sc.get("ws")}


def load_rows(ep_dir: str, split: str) -> list:
    rows = []
    vdir = os.path.basename(os.path.dirname(ep_dir))
    scene = scene_of(ep_dir)
    for line in open(os.path.join(ep_dir, "labels.jsonl")):
        x = json.loads(line)
        check_row(x, split)
        if x["drop"] is not None:
            continue
        c = os.path.join(ep_dir, "calls", f"c{x['call']:03d}")
        rows.append(dict(x, id=f"{vdir}_{x['task']}_s{x['seed']}_c{x['call']:03d}",
                         episode=os.path.basename(ep_dir) + "_" + vdir, call_dir=c, vdir=vdir, scene=scene,
                         depth_path=os.path.join(c, "head_depth.npz"), cams_path=os.path.join(c, "cams.json")))
    return rows


def _write(p: str, text: str) -> str:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return p


def _read(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


def noisy_depth(r: dict, out_dir: str, preset: str) -> tuple:
    """Write the stereo-like noisy copy of a call's head depth (depth_noise.stereo_noise, seed from the row id) ->
    (path, info). The ring-only head PNG is the RGB for the low-texture rule (no grid lines drawn on it)."""
    import hashlib

    from PIL import Image

    from .depth_noise import stereo_noise
    p = os.path.join(out_dir, f"depth_{preset}", r["id"] + ".npz")
    cams = json.load(open(r["cams_path"]))
    rgb = np.asarray(Image.open(os.path.join(r["call_dir"], "img1_head_ring.png")).convert("RGB"))
    seed = int(hashlib.sha256(r["id"].encode()).hexdigest()[:8], 16)
    d, info = stereo_noise(np.load(r["depth_path"])["depth"], rgb, float(cams["head"]["fx"]), preset, seed=seed)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.savez_compressed(p, depth=d)
    return p, info


def build(root: str, out_dir: str, split: str, fmt: str = "v2", tags: bool = False, seed: int = 0,
          repeats: bool | None = None, aux: bool = True, depth_noise: str | None = None) -> dict:
    """depth_noise: None (perfect simulator depth) or a depth_noise.PRESETS name -> every row's depth_path points to
    a noisy copy (track D against realistic depth; the images and answers are unchanged)."""
    if fmt not in FORMATS:
        raise ValueError(f"format {fmt!r}: one of {FORMATS}")
    from ..teach_strip8 import strip as ST
    repeats = (split == "train") if repeats is None else repeats
    arm = PT_ARM[fmt]
    dirs = episode_dirs(root)
    base = [r for d in dirs for r in load_rows(d, split)]
    rng = np.random.default_rng([seed, PD.ARMS.index(arm)])
    pdir = os.path.join(out_dir, "prompts", f"{split}_{fmt}" + ("_tags" if tags else ""))
    ctrl = []
    for r in base:
        x = PD.arm_row(r, arm, keep_unlabelled=split != "train")
        if x is None:
            continue
        x = dict(x, format=fmt, tags=bool(tags))
        if fmt == "s-min":
            x["prompt_path"] = _write(os.path.join(pdir, x["id"] + ".txt"),
                                      (TAG_LINES if tags else "") + ST.minimal(_read(os.path.join(x["call_dir"],
                                                                                                    "prompt_v2.txt"))))
        elif tags:
            x["prompt_path"] = _write(os.path.join(pdir, x["id"] + ".txt"), TAG_LINES + _read(x["prompt_path"]))
        if depth_noise:
            x["depth_path"], x["depth_noise"] = noisy_depth(x, out_dir, depth_noise)
        ctrl.append(x)
    rows = []
    for r in ctrl:
        rows += [r] * (repeat_of(r) if repeats else 1)
    auxr = []
    if aux:
        for r in ctrl:
            a = PD.aux_for(r, arm, rng)
            if a is None:
                continue
            a = dict(a, format=fmt, tags=bool(tags), scene=r["scene"],
                     prompt=(TAG_LINES if tags else "") + a["prompt"])
            auxr.append(a)
    os.makedirs(out_dir, exist_ok=True)
    name = f"{split}_{fmt}" + ("_tags" if tags else "") + (f"_{depth_noise}" if depth_noise else "")
    with open(os.path.join(out_dir, name + ".jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows + auxr:
            f.write(json.dumps(r) + "\n")
    eps = {}
    for d in dirs:
        m = json.load(open(os.path.join(d, "meta.json")))
        eps[d] = (m, scene_of(d))
    counts = {"split": split, "format": fmt, "tags": bool(tags), "depth_noise": depth_noise, "episodes": len(dirs),
              "episodes_success": sum(bool(m["success"]) for m, _ in eps.values()),
              "rows_labelled": len(base), "control_unique": len(ctrl), "control_rows": len(rows),
              "aux_rows": len(auxr), "total": len(rows) + len(auxr),
              "by_task": dict(Counter(r["task"] for r in ctrl)),
              "by_table_z": dict(sorted(Counter(f"{r['scene']['table_z']:.3f}" for r in ctrl).items())),
              "by_height_bin": dict(Counter(r["scene"]["height_bin"] for r in ctrl)),
              "by_dist_bin": dict(Counter(r["scene"]["dist_bin"] for r in ctrl)),
              "by_variant": dict(Counter(r["variant"] for r in ctrl)),
              "by_step": dict(Counter(r["step"] for r in ctrl)),
              "by_aux_kind": dict(Counter(r["aux_kind"] for r in auxr)),
              "episodes_by_task_height": dict(sorted(Counter(f"{s['task']}|{s['table_z']:.3f}"
                                                             for _, s in eps.values()).items())),
              "episodes_by_dist_bin": dict(Counter(s["dist_bin"] for _, s in eps.values())),
              "episodes_by_variant_height": dict(sorted(Counter(f"{s['variant']}|{s['table_z']:.3f}"
                                                                for _, s in eps.values()).items())),
              "clean_success_by_task": {t: [sum(1 for m, s in eps.values() if s["task"] == t and m["style"] == "clean"),
                                            sum(1 for m, s in eps.values() if s["task"] == t and m["style"] == "clean"
                                                and m["success"])] for t in sorted({s["task"] for _, s in eps.values()})}}
    with open(os.path.join(out_dir, name + ".counts.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(counts, f, indent=1)
    return counts
