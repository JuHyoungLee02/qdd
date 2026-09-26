"""E-STRIP8 data (prereg_strip8.md §2): the arms reuse the E-PT nd-xyz rows (harvest.teach_pt.dataset: the same L8
behaviour states, L8 truth labels, repeats and aux QA on the ring-only head image) and change only the control
request.
  s-min   every control row: strip.minimal(prompt_v2.txt of the call) on the ring-only head image (train and eval)
  s-drop  training only: per control-row occurrence (repeats drawn separately) a dropout draw strip.sample_drops
          (all fields with p 0.3, else each field with p 0.5); text = strip.strip(prompt_v2.txt, draw); head image =
          the v2 grid / drop-line image when 'overlay' is kept, the ring-only image when it is dropped
  s-stale evaluation only (OOD-H): the v2 request with a HAND-WRITTEN table height stale_z (0.850 = the value in the
          prompt code) instead of the scene's true one: table line and workspace z from stale_z, grid / drop line
          redrawn at stale_z on the ring-only image (the ring is redrawn on top, so at the true height the image is
          the saved v2 image pixel for pixel), the v2 "outside the image" note from the redrawn elements
Aux rows are copied unchanged. Every control row is checked: strip(v2, {table, overlay}) must equal the saved nd-xyz
request of the same call (the arms differ from nd-xyz only by the stripped fields); a mismatch stops the build.
Prompt files -> <out>/prompts/<split>_<arm>/<id>[_o<k>].txt; rows -> <out>/<split>_<arm>.jsonl (+ .counts.json)."""
from __future__ import annotations

import json
import os
from collections import Counter

import numpy as np

from . import strip as S

ARMS = ("s-min", "s-drop", "s-stale")
V2_HEAD = "img1_head_camera.png"
RING_HEAD = "img1_head_ring.png"


def _read(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


def stale_request(r: dict, v2: str, stale_z: float, png_out: str) -> str:
    """-> the v2 request text with the table height stale_z; writes the redrawn head image to png_out."""
    from PIL import Image

    from ..astra_motion.executor import SAFE_DZ
    from ..astra_motion.geometry import Cam
    from ..astra_solo.overlay import head_overlay
    m = S._TABLE_RE.search(v2)
    if m is None:
        raise ValueError(f"no v2 table line in {r['id']}")
    x0, x1, y0, y1 = (float(v) for v in m.groups())
    line = (f"- Table top surface: z = {stale_z:.3f} m. The code keeps the TCP inside x {x0:.2f}..{x1:.2f}, y "
            f"{y0:.2f}..{y1:.2f}, z {stale_z + SAFE_DZ[0]:.3f}..{stale_z + SAFE_DZ[1]:.3f} m (targets beyond are "
            f"clipped, and you are told).")
    t = v2[:m.start()] + line + v2[m.end():]
    for note in (S._NOTE_TCP_V2, S._NOTE_DROP_V2):
        if t.endswith(note):
            t = t[:-len(note)]
    cam = Cam.from_json(json.load(open(r["cams_path"]))["head"])
    ring = np.asarray(Image.open(os.path.join(r["call_dir"], RING_HEAD)).convert("RGB"))
    img, drawn = head_overlay(ring, cam, stale_z, r["gt"]["tcp"])
    Image.fromarray(np.asarray(img)[..., :3]).save(png_out)
    if "tcp" not in drawn:
        t += S._NOTE_TCP_V2
    elif "drop" not in drawn:
        t += S._NOTE_DROP_V2
    return t


def build(src: str, out_dir: str, split: str, arm: str, seed: int = 0, stale_z: float = 0.85) -> dict:
    if arm not in ARMS:
        raise ValueError(arm)
    if arm == "s-drop" and split != "train":
        raise ValueError("s-drop is a training arm; evaluation uses the minimal request (s-min rows)")
    if arm == "s-stale" and split != "ood_h":
        raise ValueError("s-stale is an OOD-H evaluation arm (at the training height it equals the v2 request)")
    rows = [json.loads(x) for x in open(src, encoding="utf-8")]
    pdir = os.path.join(out_dir, "prompts", f"{split}_{arm}")
    os.makedirs(pdir, exist_ok=True)
    rng = np.random.default_rng([seed, 8, 97])
    seen: Counter = Counter()
    out, drop_sets, field_counts, n_ctrl, n_aux = [], Counter(), Counter(), 0, 0
    for r in rows:
        if r["kind"] != "control":
            out.append(r)
            n_aux += 1
            continue
        n_ctrl += 1
        v2 = _read(os.path.join(r["call_dir"], "prompt_v2.txt"))
        if S.strip(v2, {"table", "overlay"}) != _read(r["prompt_path"]):
            raise ValueError(f"v2 -> nd-xyz identity fails for {r['id']}")
        k = seen[r["id"]]
        seen[r["id"]] += 1
        name = r["id"] + ("_o%d" % k if arm == "s-drop" else "")
        p = os.path.join(pdir, name + ".txt")
        extra = {}
        if arm == "s-stale":
            drops = frozenset()
            head = os.path.join(pdir, name + "_head.png")
            text = stale_request(r, v2, stale_z, head)
            extra = {"stale_z": round(float(stale_z), 4)}
        else:
            drops = frozenset(S.FIELDS) if arm == "s-min" else S.sample_drops(rng)
            text = S.strip(v2, drops)
            head = os.path.join(r["call_dir"], RING_HEAD if "overlay" in drops else V2_HEAD)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        if not os.path.exists(head):
            raise ValueError(f"missing head image {head}")
        out.append(dict(r, arm=arm, prompt_path=p, images=[head] + list(r["images"][1:]), drops=sorted(drops),
                        **extra))
        drop_sets["+".join(sorted(drops)) or "(none)"] += 1
        for f_ in drops:
            field_counts[f_] += 1
    dst = os.path.join(out_dir, f"{split}_{arm}.jsonl")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    counts = {"src": src, "split": split, "arm": arm, "seed": seed, "rows": len(out), "control_rows": n_ctrl,
              "control_unique": len(seen), "aux_rows": n_aux, "drop_sets": dict(sorted(drop_sets.items())),
              "field_drop_counts": {f_: field_counts[f_] for f_ in S.FIELDS},
              "field_drop_rate": {f_: round(field_counts[f_] / max(n_ctrl, 1), 4) for f_ in S.FIELDS}}
    with open(dst + ".counts.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(counts, f, indent=1)
    return counts
