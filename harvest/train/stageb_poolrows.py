"""Stage-B rows for the POOL (seeds 2000-2119) with SYNTHETIC actions -- smoke checkpoints only (pre-R7 fix 1).

The pool has 0.33 s snapshots (images, text_state, privileged state, labels_v2 decisions) but no 30 Hz action
stream, so action_exec = the snapshot's own 8-D command held for H steps (a "hold" chunk). Everything else is real:
proprio from the snapshot npz (q, qd of the right arm; tau = joint_effort_target -- the pool has no measured
torque), aux geometry (datagen.rows.aux_row), verification-head targets = the E-M4b test predicates of the snapshot
(m4b.data.pool_truth). Rows are flagged synthetic_actions = true and written OUTSIDE the pool folder.

  python -m harvest.train.stageb_poolrows --pool /data/harvest/data/pool --out FILE [--splits fit,eval]
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np

ARM_IDS = (6, 11, 14, 16, 18, 20, 22)  # arm_r_joint1..7 in the robot's 31 joints (m4b fidev robot_meta.json)


def pool_row(line: dict, z, H: int = 15) -> dict:
    from ..datagen.rows import aux_row, skill_of
    from ..m4b.data import pool_truth
    k = int(line["k"])
    ids = list(ARM_IDS)
    act = [round(float(v), 6) for v in np.asarray(z["action"][k], float)]
    grip_w = float(line["state"]["obs"]["raw"]["grip"]["w"])
    tr = pool_truth(line)
    return {"seed": int(line["seed"]), "kind": line.get("kind"), "k": k, "hz": 30, "H": H, "arm": "right",
            "skill_id": skill_of(line["phase"]), "phase_id": line["phase"],
            "proprio": {"q": np.asarray(z["joint_pos"][k], float)[ids].tolist(),
                        "qd": np.asarray(z["joint_vel"][k], float)[ids].tolist(),
                        "tau": np.asarray(z["joint_effort_target"][k], float)[ids].tolist(),
                        "grip": [grip_w, 0.0]},
            "action_exec": [act] * H, "action_script": [act] * H, "valid": [1] * H,
            "aux": aux_row(line["state"], "o3", "o5"),
            "verify": {"truth": {p: (None if v is None else bool(v)) for p, v in tr.items()}},
            "synthetic_actions": True}


def build(pool_dir: str, out: str, splits=("fit", "eval"), H: int = 15) -> int:
    from .stageb_data import check_row
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for p in sorted(glob.glob(f"{pool_dir}/ep*.jsonl"), key=lambda x: int(os.path.basename(x)[2:-6])):
            lines = [json.loads(x) for x in open(p, encoding="utf-8")]
            if not lines or lines[0].get("split") not in splits:
                continue
            z = np.load(p[:-6] + ".npz")
            for ln in lines:
                r = pool_row(ln, z, H)
                check_row(r)
                f.write(json.dumps(r) + "\n")
                n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="/data/harvest/data/pool")
    ap.add_argument("--out", required=True)
    ap.add_argument("--splits", default="fit,eval")
    a = ap.parse_args(argv)
    if os.path.abspath(a.out).startswith(os.path.abspath(a.pool) + os.sep):
        raise SystemExit("write the synthetic rows outside the pool folder")
    print(json.dumps({"rows": build(a.pool, a.out, tuple(a.splits.split(","))), "out": a.out}))


if __name__ == "__main__":
    main()
