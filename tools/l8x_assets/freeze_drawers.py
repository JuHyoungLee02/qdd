"""Freeze the drawer task list before its gate (prereg_l8x_tasks 0 / change 6): top-down graspable handles from
handle_topdown.py output, split by piece-name hash (20 % ood), gate picks 35350-35359 (change 10), digest.
usage: python tools/l8x_assets/freeze_drawers.py HANDLES.json OUT.json"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.teach_l8d import xdrawer as XD  # noqa: E402

GATE = range(35350, 35360)  # change 10 (gate 5, L8D range); gate 4 35345 / gate 3 35330 aborted, gate 2 35390-35399


def split_of(piece: str) -> str:
    return "ood" if int(hashlib.sha256(f"l8x-drawer-ood:{piece}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < 0.2 \
        else "train"


def main(argv=None):
    a = argv or sys.argv[1:]
    items = XD.drawer_list(json.load(open(a[0])))
    rows = [{"task": XD.task_id(p, b), "piece": p, "handle_body": b, "handle_top_z": z, "split": split_of(p)}
            for p, b, z in items]
    train = [r for r in rows if r["split"] == "train"]
    gate = {str(s): XD.gate_pick(train, s)["task"] for s in GATE}
    out = {"tasks": rows, "gate": gate}
    out["digest"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
    json.dump(out, open(a[1], "w"), indent=1)
    print(len(rows), "handles;", {s: sum(r["split"] == s for r in rows) for s in ("train", "ood")},
          "pieces", len({r["piece"] for r in rows}))
    print("gate", gate)


if __name__ == "__main__":
    main()
