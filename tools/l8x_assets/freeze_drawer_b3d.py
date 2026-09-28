"""Freeze the b3d drawer bundle list (prereg_l8x_tasks change 12): every handle of l8x_drawer_list.json (11 handles,
4 pieces), one piece held out as OOD (OOD_PIECE, never trained), handle_y (scene frame, the robot's left = +y) for the
drawer wording, and the TRAIN plan: seeds 34652-34799 over the train handles, balanced (round-robin over a seeded
shuffle). Plan rows are run_collect --plan rows (furniture "drawer", variant standard).
usage: python tools/l8x_assets/freeze_drawer_b3d.py HANDLES.json docs/stage3/l8x_drawer_list.json OUT.json
(also writes OUT_plan.json = the plan list for run_collect --plan)"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.teach_l8d import xdrawer as XD  # noqa: E402

OOD_PIECE = "Desk_306_1"  # the only desk (a different furniture kind): held out
EXCLUDED = ("Dresser_210_1_1",)  # change 14: 28 mm behind the bar -- the front grasp is blocked (b3d 8/30, 0/4 re-run)
TRAIN_SEEDS = range(34652, 34800)


def handle_y(handles_json: dict, piece: str, body: str) -> float:
    best = None
    for hd in handles_json[piece]["handles"]:
        if XD.handle_body(hd["prim"]) == body and (best is None or hd["size"][1] > best["size"][1]):
            best = hd
    return round(float(best["centre"][1]), 3)


def freeze(handles_json: dict, lst: dict) -> dict:
    rows = [dict(r, handle_y=handle_y(handles_json, r["piece"], r["handle_body"]),
                 split="ood" if r["piece"] == OOD_PIECE else "excluded" if r["piece"] in EXCLUDED else "train")
            for r in lst["tasks"]]
    first = sorted(r["task"] for r in rows if r["split"] != "ood")  # the change-12 order (seed -> task kept)
    order = sorted(first, key=lambda t: hashlib.sha256(f"b3d:{t}".encode()).hexdigest())
    keep = [t for t in order if t.split("__")[1] not in EXCLUDED]
    plan, n_moved = [], 0
    for k, s in enumerate(TRAIN_SEEDS):
        t = order[k % len(order)]
        if t.split("__")[1] in EXCLUDED:  # change 14: its seeds go to the kept handles in turn
            t, n_moved = keep[n_moved % len(keep)], n_moved + 1
        plan.append({"seed": s, "task": t, "variant": "standard", "split": "train", "objset": None,
                     "furniture": "drawer", "table_z": 0.0})
    out = {"tasks": rows, "ood_piece": OOD_PIECE, "plan": plan, "source_digest": lst["digest"]}
    out["digest"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
    return out


def main(argv=None):
    a = argv or sys.argv[1:]
    out = freeze(json.load(open(a[0])), json.load(open(a[1])))
    json.dump(out, open(a[2], "w", newline="\n"), indent=1)
    json.dump(out["plan"], open(a[2].replace(".json", "_plan.json"), "w", newline="\n"))  # run_collect --plan
    from collections import Counter
    print(len(out["tasks"]), "handles;", dict(Counter(r["split"] for r in out["tasks"])), "plan", len(out["plan"]),
          dict(Counter(e["task"].split("__")[1] for e in out["plan"])))


if __name__ == "__main__":
    main()
