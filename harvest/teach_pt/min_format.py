"""E-DIST8 minimal-input requests for the three output tracks R / H / D (prereg_dist8.md §1; canon §98 supp 1).
All three start from the SAME minimal request of a state: E-STRIP8's S-min (harvest.teach_strip8.strip.minimal of the
call's astra-solo@v2 request: no table height, no grid / drop line, no object sizes, no recipes; ring-only head image)
— provisional until the STRIP8 re-verification on L8-X. Only the command part and the answer form differ:
  R  (= S-min)  v2 commands, xyz answer                                              image: ring head, wrist
  D  (d-min)    the eef bullet -> the point bullet + the POINT, THEN ACT block of astra-solo-pt@v1 (the height-intent
                definitions are the interface, not a recipe); pt answer; target = depth converter    ring head, wrist
  H  (h-min)    the R request + depth tag + hybrid hint / answer (point + intent AND xyz); + the encoded depth image
                when depth is present (hybrid.py)
Rows (teach_l8 format): build(root, out_dir, split, track, mode) — train rows get L8 repeats and one aux row per state
(R / H: the nd robot-frame xy QA on the ring image; D: the pointing QA on the ring image), evaluation rows keep every
state (label_missing when the point label did not verify; scored on the simulator objects). H train rows: depth off
(p 0.5) / zed_mini noise (half of the kept) / clean, from the row id; H evaluation modes on / noisy / off; D
evaluation modes on / noisy."""
from __future__ import annotations

import json
import os
from collections import Counter

import numpy as np

from ..astra_solo import hybrid as HY
from ..astra_solo import nd_prompts as NP
from ..astra_solo import prompts as V2P
from ..astra_solo import pt_prompts as PT
from ..teach_l8.dataset import IMAGE_FILES, episode_dirs, repeat_of
from ..teach_strip8 import strip as S
from . import dataset as DS

TRACKS = ("r-min", "d-min", "h-min")
RING = "img1_head_ring.png"
_PT_BLOCK = PT.STATIC[PT.STATIC.index("POINT, THEN ACT"):PT.STATIC.index("FRAME AND UNITS")]
_PT_BULLET = PT.STATIC[PT.STATIC.index("- point: move the TCP"):].split("\n", 1)[0]
_PT_AUX_HEAD = "Image 1 is the robot's head camera (the white ring is the gripper's TCP).\n"


def r_text(v2: str) -> str:
    return S.minimal(v2)


def _split(t: str) -> tuple:
    if t.count(V2P.ANSWER) != 1:
        raise ValueError("not a v2-answer request")
    return t.split(V2P.ANSWER)


def d_text(v2: str) -> str:
    prefix, note = _split(r_text(v2))
    if prefix.count(NP._EEF_V2) != 1 or prefix.count("FRAME AND UNITS") != 1:
        raise ValueError("min request without the eef bullet / frame section")
    prefix = prefix.replace(NP._EEF_V2, _PT_BULLET).replace("FRAME AND UNITS", _PT_BLOCK + "FRAME AND UNITS")
    return prefix + PT.ANSWER + note


def h_text(v2: str, depth: bool) -> str:
    prefix, note = _split(r_text(v2))
    return HY.request(prefix + note, "", depth)


def _write(out_dir: str, sub: str, name: str, text: str) -> str:
    p = os.path.join(out_dir, "prompts_min", sub, name + ".txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return p


def _depth(r: dict, out_dir: str, dm: str):
    if dm == "off":
        return None
    if dm == "clean":
        return r["depth_path"]
    from ..teach_l8d.dataset import noisy_depth
    return noisy_depth(r, out_dir, "zed_mini")[0]


def row(r: dict, out_dir: str, track: str, dm: str = "clean") -> dict:
    v2 = open(os.path.join(r["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
    ims = [os.path.join(r["call_dir"], RING), os.path.join(r["call_dir"], IMAGE_FILES[1])]
    base = dict(r, kind="control", arm=track, xyz_answer=r["answer"])
    if track == "r-min":
        return dict(base, prompt_path=_write(out_dir, "r", r["id"], r_text(v2)), images=ims, answer=r["answer"],
                    label_missing=False)
    if track == "d-min":
        miss = r.get("pt_answer") is None
        txt, ans = d_text(v2), r["answer"] if miss else r["pt_answer"]
        if r.get("hand"):  # L9 (spec §4, opt-in): the used arm; rows without it (L8S) are unchanged
            from ..l9.hand import add_hand_format, left_text, with_hand
            txt = add_hand_format(left_text(txt) if r["hand"] == "left" else txt)
            ans = ans if miss else with_hand(ans, r["hand"])
        return dict(base, prompt_path=_write(out_dir, "d", r["id"], txt), images=ims,
                    answer=ans, label_missing=miss, depth_path=_depth(r, out_dir, dm),
                    d_mode=dm)
    if track == "h-min":
        dp = _depth(r, out_dir, dm)
        if dp is not None:
            pp = os.path.join(out_dir, "h_depth", f"{r['id']}_{dm}.png")
            os.makedirs(os.path.dirname(pp), exist_ok=True)
            with open(pp, "wb") as f:
                f.write(HY.depth_png(np.load(dp)["depth"]))
            ims = ims + [pp]
        return dict(base, prompt_path=_write(out_dir, f"h_{dm}", r["id"], h_text(v2, dp is not None)), images=ims,
                    depth_path=dp, h_mode=dm, answer=HY.h_answer(r["answer"], r.get("pt_answer")),
                    label_missing=r.get("pt_answer") is None)
    raise ValueError(track)


def _aux(x: dict, track: str, rng):
    if track == "d-min":
        a = DS.aux_for(x, "pt", rng)
        if a is None:
            return None
        return dict(a, arm=track, images=[os.path.join(x["call_dir"], RING)],
                    prompt=a["prompt"].replace(DS.PT_HEAD, _PT_AUX_HEAD))
    a = DS.aux_for(x, "nd-xyz", rng)
    return None if a is None else dict(a, arm=track)


def convert(src: str, out_dir: str, track: str, dst_name: str) -> dict:
    """Training rows from an existing E-PT-format arm file (teach_pt.dataset rows: train_pt for D, train_nd-xyz for H /
    R) — same states, repeats and aux draws, only the request / head image / answer re-made as the min track; the aux
    rows keep their answers (D: the verified pointing pixels; R / H: the robot-frame xy) on the ring head image. Fast
    path for large sets (no depth re-resolution for the aux pixels)."""
    if track not in TRACKS:
        raise ValueError(track)
    rows = [json.loads(x) for x in open(src, encoding="utf-8")]
    cache, out, n_c, n_a = {}, [], 0, 0
    modes = Counter()
    for r in rows:
        if r["kind"] == "aux":
            ring = os.path.join(os.path.dirname(r["images"][0]), RING)
            a = dict(r, arm=track, images=[ring])
            if track == "d-min":
                a["prompt"] = r["prompt"].replace(DS.PT_HEAD, _PT_AUX_HEAD)
            out.append(a)
            n_a += 1
            continue
        if r["id"] not in cache:
            dm = HY.train_depth_mode(r["id"]) if track == "h-min" else "clean"
            src_row = dict(r, answer=r.get("xyz_answer", r["answer"]))  # arm files carry the arm answer in 'answer'
            cache[r["id"]] = row(src_row, out_dir, track, dm)
            modes[cache[r["id"]].get("h_mode") or "clean"] += 1
        out.append(cache[r["id"]])
        n_c += 1
    with open(os.path.join(out_dir, dst_name), "w", encoding="utf-8", newline="\n") as f:
        for x in out:
            f.write(json.dumps(x) + "\n")
    counts = {"src": src, "control_rows": n_c, "aux_rows": n_a, "states": len(cache), "depth_modes": dict(modes)}
    with open(os.path.join(out_dir, dst_name + ".counts.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(counts, f, indent=1)
    return counts


def build(root: str, out_dir: str, split: str, track: str, mode: str = "clean", seed: int = 0) -> dict:
    """mode: train -> per-row depth draw (H) / clean (D); evaluation: clean | noisy | off (off for H only)."""
    if track not in TRACKS:
        raise ValueError(track)
    train = split == "train"
    base = [r for d in episode_dirs(root) for r in DS.load_rows(d, split)]
    rng = np.random.default_rng([seed, TRACKS.index(track), 29])
    rows, auxr = [], []
    for r in base:
        if track == "h-min":
            dm = HY.train_depth_mode(r["id"]) if train else mode
        else:
            dm = "clean" if train else mode
        x = row(r, out_dir, track, dm)
        if train and x["label_missing"] and track == "d-min":
            continue  # a D training row needs a verified point label (E-PT rule)
        rows += [x] * (repeat_of(x) if train else 1)
        if train:
            a = _aux(x, track, rng)
            if a is not None:
                auxr.append(a)
    name = f"{split}_{track}" + ("" if train else f"_{mode}")
    with open(os.path.join(out_dir, name + ".jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for x in rows + auxr:
            f.write(json.dumps(x) + "\n")
    counts = {"states": len(base), "control_rows": len(rows), "aux_rows": len(auxr),
              "label_missing": sum(bool(x["label_missing"]) for x in rows),
              "depth_modes": dict(Counter(x.get("h_mode") or x.get("d_mode") or "none" for x in rows))}
    with open(os.path.join(out_dir, name + ".counts.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(counts, f, indent=1)
    return counts
