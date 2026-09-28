"""Freeze the new-task lists before any gate (prereg_l8x_tasks 0): stack pairs and push objects per split, the gate
picks (seed -> task) and a digest -> docs/stage3/l8x_tasks_lists.json.
usage: python tools/l8x_assets/freeze_new_tasks.py OUT.json"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.teach_l8d import xnew as XN  # noqa: E402

GATE = {"stack": range(35200, 35210), "push": range(35210, 35220)}


def main(argv=None):
    a = argv or sys.argv[1:]
    rows = XN.load_real_rows()
    out = {"table_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()}
    for split in ("train", "ood_o"):
        out[split] = {"stack": [XN.stack_task_id(x, y) for x, y in XN.stack_pairs(rows, split)],
                      "push": [XN.push_task_id(x) for x in XN.push_objects(rows, split)]}
    gate = {}
    for kind, seeds in GATE.items():
        pool = out["train"][kind]
        for s in seeds:
            gate[str(s)] = pool[XN._h(f"gate:{kind}:{s}") % len(pool)] if pool else None
    out["gate"] = gate
    out["digest"] = hashlib.sha256(json.dumps({k: out[k] for k in ("train", "ood_o", "gate")},
                                              sort_keys=True).encode()).hexdigest()
    with open(a[0], "w") as f:
        json.dump(out, f, indent=1)
    for split in ("train", "ood_o"):
        print(split, {k: len(v) for k, v in out[split].items()})
    print("gate", gate)


if __name__ == "__main__":
    main()
