"""Track-H and D-noisy rows from collected E-PT / L8-X episodes (the teach_l8 row format; train.py / evaluate.py read
them unchanged) — design docs/research/rgb_depth_hybrid_survey_2026-09-27.md §4-§5.
  build_h(mode):  train  per call depth 'off' (p 0.5) / 'noisy' (zed_mini, half of the kept) / 'clean', from the row id
                  on / noisy / off  evaluation: every state with sim depth / stereo-noise depth / no depth
      request = hybrid.request(the saved nd-xyz@v1 request's body + NOW, depth present?) (= the R request apart from
      the depth line and the answer form, gate G-same); images = ring-only head, right wrist (+ the encoded depth
      when present); answer = hybrid.h_answer(xyz truth, pt truth) — point + height AND xyz whenever both exist.
      Train rows get L8's repeats and one aux row per state (the nd-xyz robot-frame xy QA on the ring image) so the
      sample count matches the other arms.
  build_pt_noisy: the pt arm's rows with the head depth replaced by its zed_mini copy (D-noisy evaluation)."""
from __future__ import annotations

import json
import os
from collections import Counter

import numpy as np

from ..astra_solo import hybrid as HY
from ..astra_solo import nd_prompts as NP
from ..teach_l8.dataset import IMAGE_FILES, episode_dirs, repeat_of
from . import dataset as DS

MODES = ("train", "on", "noisy", "off")


def _depth_npz(r: dict, out_dir: str, dm: str) -> str:
    if dm == "clean":
        return r["depth_path"]
    from ..teach_l8d.dataset import noisy_depth
    return noisy_depth(r, out_dir, "zed_mini")[0]


def h_row(r: dict, out_dir: str, dm: str) -> dict:
    nd = open(os.path.join(r["call_dir"], "prompt_nd-xyz@v1.txt"), encoding="utf-8").read()
    ans_nd = NP.ANSWERS["nd-xyz@v1"]
    if nd.count(ans_nd) != 1:
        raise ValueError(f"{r['id']}: not an nd-xyz@v1 request")
    prefix, note = nd.split(ans_nd)
    text = HY.request(prefix + note, "", dm != "off")
    tp = os.path.join(out_dir, "h_prompts", f"{r['id']}_{dm}.txt")
    os.makedirs(os.path.dirname(tp), exist_ok=True)
    with open(tp, "w", encoding="utf-8") as f:
        f.write(text)
    ims = [os.path.join(r["call_dir"], "img1_head_ring.png"), os.path.join(r["call_dir"], IMAGE_FILES[1])]
    depth_path = None
    if dm != "off":
        depth_path = _depth_npz(r, out_dir, dm)
        pp = os.path.join(out_dir, "h_depth", f"{r['id']}_{dm}.png")
        os.makedirs(os.path.dirname(pp), exist_ok=True)
        with open(pp, "wb") as f:
            f.write(HY.depth_png(np.load(depth_path)["depth"]))
        ims.append(pp)
    return dict(r, kind="control", arm="h", h_mode=dm, prompt_path=tp, images=ims, depth_path=depth_path,
                answer=HY.h_answer(r["answer"], r.get("pt_answer")), xyz_answer=r["answer"],
                label_missing=r.get("pt_answer") is None)


def build_h(root: str, out_dir: str, split: str, mode: str, seed: int = 0) -> dict:
    if mode not in MODES or (mode == "train") != (split == "train"):
        raise ValueError(f"mode {mode} with split {split}")
    base = [r for d in episode_dirs(root) for r in DS.load_rows(d, split)]
    rng = np.random.default_rng([seed, 17])
    rows, auxr = [], []
    for r in base:
        dm = HY.train_depth_mode(r["id"]) if mode == "train" else {"on": "clean", "noisy": "noisy", "off": "off"}[mode]
        x = h_row(r, out_dir, dm)
        rows += [x] * (repeat_of(x) if mode == "train" else 1)
        if mode == "train":
            a = DS.aux_for(dict(x, call_dir=r["call_dir"]), "nd-xyz", rng)
            if a is not None:
                auxr.append(dict(a, arm="h"))
    name = f"{split}_h" + ("" if mode == "train" else f"_{mode}")
    with open(os.path.join(out_dir, name + ".jsonl"), "w") as f:
        for x in rows + auxr:
            f.write(json.dumps(x) + "\n")
    counts = {"states": len(base), "control_rows": len(rows), "aux_rows": len(auxr),
              "depth_modes": dict(Counter(x["h_mode"] for x in rows)),
              "point_missing": sum(bool(x["label_missing"]) for x in rows)}
    with open(os.path.join(out_dir, name + ".counts.json"), "w") as f:
        json.dump(counts, f, indent=1)
    return counts


def build_pt_noisy(root: str, out_dir: str, split: str) -> dict:
    base = [r for d in episode_dirs(root) for r in DS.load_rows(d, split)]
    rows = []
    for r in base:
        x = DS.arm_row(r, "pt", keep_unlabelled=True)
        rows.append(dict(x, depth_path=_depth_npz(r, out_dir, "noisy"), depth_noise="zed_mini"))
    with open(os.path.join(out_dir, f"{split}_pt_noisy.jsonl"), "w") as f:
        for x in rows:
            f.write(json.dumps(x) + "\n")
    return {"states": len(rows)}
