"""Paired effort comparison without Isaac (prereg §5 P2): re-send saved call inputs (the exact prompt text of the first
attempt and its two PNG images) to another model / effort and score the new command against the call's stored truth
(xy error of the commanded TCP target to the target object while approaching, to the place object while carrying).
Only first-attempt, valid, scored calls (approach / carry, eef or edit) are re-asked, in episode and call order.
An edit's goal = the measured TCP at the call + delta (the executor's commanded reference is within 3 cm of it)."""
from __future__ import annotations

import glob
import json
import os

import numpy as np

from . import schema as SC
from .prompts import IMAGE_LABELS


def goal_of(cmd: dict, truth: dict):
    if cmd["mode"] == "eef":
        return [float(v) for v in cmd["position_m"]]
    if cmd["mode"] == "edit":
        return [round(float(a + b), 6) for a, b in zip(truth["tcp"], cmd["delta_m"])]
    return None


def xy_err_mm(goal, truth: dict, phase: str) -> float:
    ref = truth["tgt_xyz"] if phase == "approach" else truth["place_xyz"]
    return round(float(np.linalg.norm(np.asarray(goal[:2]) - np.asarray(ref[:2]))) * 1e3, 1)


def reask(episode_dirs: list, model, max_calls: int, out_path: str | None = None) -> list:
    rows = []
    for ep in episode_dirs:
        res = json.load(open(os.path.join(ep, "result.json")))
        for c in res["calls"]:
            if len(rows) >= max_calls:
                return rows
            if not (c.get("valid") and c.get("attempt") == 0 and c.get("score")):
                continue
            d = os.path.join(ep, "calls", f"c{c['call']:03d}")
            text = open(os.path.join(d, "prompt.txt"), encoding="utf-8").read()
            ims = []
            for j, lab in enumerate(IMAGE_LABELS):
                ims.append((lab, open(os.path.join(d, f"img{j + 1}_{lab.replace(' ', '_')}.png"), "rb").read()))
            rep = model.ask(text, ims, {"kind": "reask", "src": ep, "call": c["call"]})
            p, err = (None, [f"api:{rep.error}"]) if (rep.error and not rep.text) else SC.validate(rep.text)
            row = {"episode": ep, "seed": res.get("seed"), "variant": res.get("variant"), "call": c["call"],
                   "phase": c["phase_truth"], "orig_xy_err_mm": c["score"]["xy_err_mm"],
                   "orig_mode": c["parsed"]["command"]["mode"], "valid": p is not None, "errors": err[:4],
                   "latency_s": round(rep.latency_s, 3), "usage": rep.usage, "cost_usd": round(rep.cost_usd, 6),
                   "model": getattr(model, "name", None)}
            if p is not None:
                g = goal_of(p["command"], c["truth"])
                row["new_mode"] = p["command"]["mode"]
                row["new_xy_err_mm"] = xy_err_mm(g, c["truth"], c["phase_truth"]) if g else None
                row["new_command"] = p["command"]
            rows.append(row)
            if out_path:
                with open(out_path, "a") as f:
                    f.write(json.dumps(row) + "\n")
    return rows


def episode_dirs(root: str) -> list:
    return sorted(os.path.dirname(p) for p in glob.glob(os.path.join(root, "*", "s*", "result.json")))
