"""E-PRIV8 (docs/stage3/prereg_priv8.md; survey docs/research/privileged_info_training_survey_2026-09-27.md §3-4):
learn from the hand-given true values (table height, object height) WITHOUT putting them into the inference input.
  m1  minimal request (strip.minimal) + "first estimate table_z and obj_h" -> answer starts with {"estimates":
      {"table_z", "obj_h"}} supervised by the simulator truth; on training rows the request / estimates are present
      with p 0.5 (else the plain minimal request and answer = the field is omitted, no loss on it); evaluation rows
      always ask (m1 keep), the plain s-min rows are the m1 drop evaluation of the same checkpoint.
  m3  training input curriculum: each control row carries the minimal request (prompt_path / images) and the full
      v2 request with the true values and the grid image (alt_prompt_path / alt_images); train_curr.py picks the v2
      variant with p_hand(progress) = 1 -> 0 over the first 60 % of the used micro-batches, 0 after; inference = minimal.
Aux rows are copied unchanged (nd aux, ring-only image)."""
from __future__ import annotations

import json
import os

import numpy as np

from . import strip as S

EST_REQUEST = ("First estimate from the images (robot frame, metres): table_z = the height of the table top; obj_h = "
               "the height of the object to move. Then assess and command.\n")
PLAIN_JSON = 'Return JSON only: {"assessment"'
EST_JSON = 'Return JSON only: {"estimates": {"table_z": number, "obj_h": number}, "assessment"'
_ANCHOR = "\nFirst assess:"
ARMS = ("m1", "m3")
P_EST_TRAIN = 0.5
HAND_END = 0.6


def m1_text(minimal_text: str) -> str:
    if _ANCHOR not in minimal_text or PLAIN_JSON not in minimal_text:
        raise ValueError("m1_text: no answer form")
    t = minimal_text.replace(_ANCHOR, "\n" + EST_REQUEST + _ANCHOR.lstrip("\n"), 1)
    return t.replace(PLAIN_JSON, EST_JSON, 1)


def m1_answer(answer: str, est: dict) -> str:
    a = json.loads(answer)
    e = {"table_z": round(float(est["table_z"]), 3), "obj_h": round(float(est["target_height_m"]), 3)}
    return json.dumps({"estimates": e, **a})


def p_hand(progress: float) -> float:
    return max(0.0, 1.0 - progress / HAND_END)


def choose(row: dict, k: int, i: int, total: int, seed: int = 0) -> dict:
    """M3: the row variant used for micro-batch k, item i (deterministic)."""
    if row.get("kind") != "control" or "alt_prompt_path" not in row:
        return row
    u = np.random.default_rng([seed, 97, k, i]).random()
    if u < p_hand(k / max(total, 1)):
        return dict(row, prompt_path=row["alt_prompt_path"], images=list(row["alt_images"]))
    return row


def build(src: str, out_dir: str, split: str, arm: str, seed: int = 0) -> dict:
    if arm not in ARMS:
        raise ValueError(arm)
    if arm == "m3" and split != "train":
        raise ValueError("m3 is a training arm; evaluation uses the s-min rows")
    rows = [json.loads(x) for x in open(src, encoding="utf-8")]
    pdir = os.path.join(out_dir, "prompts", f"{split}_{arm}")
    os.makedirs(pdir, exist_ok=True)
    rng = np.random.default_rng([seed, 8, 98])
    p_est = P_EST_TRAIN if split == "train" else 1.0
    seen: dict = {}
    out, n_ctrl, n_est = [], 0, 0
    for r in rows:
        if r["kind"] != "control":
            out.append(r)
            continue
        n_ctrl += 1
        v2p = os.path.join(r["call_dir"], "prompt_v2.txt")
        v2 = open(v2p, encoding="utf-8").read()
        if S.strip(v2, {"table", "overlay"}) != open(r["prompt_path"], encoding="utf-8").read():
            raise ValueError(f"v2 -> nd-xyz identity fails for {r['id']}")
        m = S.minimal(v2)
        k = seen.get(r["id"], 0)
        seen[r["id"]] = k + 1
        if arm == "m1":
            est = rng.random() < p_est
            n_est += est
            name = f"{r['id']}_o{k}_{'e' if est else 'p'}"
            text = m1_text(m) if est else m
            ans = m1_answer(r["answer"], r["est"]) if est else r["answer"]
            extra = {"m1_est": bool(est), "answer": ans}
        else:
            name, text = f"{r['id']}_o{k}", m
            extra = {"alt_prompt_path": v2p,
                     "alt_images": [os.path.join(r["call_dir"], "img1_head_camera.png")] + list(r["images"][1:])}
        p = os.path.join(pdir, name + ".txt")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        ring = os.path.join(r["call_dir"], "img1_head_ring.png")
        out.append(dict(r, arm=arm, prompt_path=p, images=[ring] + list(r["images"][1:]), **extra))
    dst = os.path.join(out_dir, f"{split}_{arm}.jsonl")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    counts = {"src": src, "split": split, "arm": arm, "rows": len(out), "control_rows": n_ctrl,
              "est_share": round(n_est / max(n_ctrl, 1), 4) if arm == "m1" else None}
    with open(dst + ".counts.json", "w") as f:
        json.dump(counts, f, indent=1)
    return counts


def est_errors(rows: list, replies: dict) -> dict:
    """|estimate - truth| of table_z and obj_h over the replies that carry an estimates block."""
    from ..astra_motion.schema import SchemaError, extract_json
    tz, oh, n = [], [], 0
    for r in rows:
        if r.get("kind") != "control" or r["id"] not in replies:
            continue
        n += 1
        try:
            e = extract_json(replies[r["id"]]["text"] or "").get("estimates")
            tz.append(abs(float(e["table_z"]) - r["est"]["table_z"]) * 1e3)
            oh.append(abs(float(e["obj_h"]) - r["est"]["target_height_m"]) * 1e3)
        except (SchemaError, AttributeError, KeyError, TypeError, ValueError):
            continue
    q = (lambda v, p: round(float(np.percentile(v, p)), 1) if v else None)
    return {"n": n, "n_est": len(tz), "table_z_abs_median_mm": q(tz, 50), "table_z_abs_p90_mm": q(tz, 90),
            "obj_h_abs_median_mm": q(oh, 50), "obj_h_abs_p90_mm": q(oh, 90)}
