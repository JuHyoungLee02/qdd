"""JCR data selection = validation filter (prereg_jcr1.md change 4; NOW.md §4 'validation-failed rows never go in').
The D0 criteria are unchanged; rows that fail them are removed, and the composition rule is met by episode selection.
  python tools/jcr/select_data.py --data /data/harvest/out/jcr/d1 --out /data/harvest/out/jcr/d1_select.json
Removed (recorded with reasons; the recording itself is never modified):
  1. episodes with a measured arm joint step > 0.04 rad per tick anywhere (D0 limit) -- d1: 5 IK / controller
     run-aways (the TCP leaves a static command by > 10 cm, 11-54 ticks up to 0.149 rad) + 15 single-tick overshoots
     (0.046-0.052 rad); 20 of 2,000
  2. samples whose label chunk breaks v <= V_MAX or a <= 1.01 A_MAX (the arrival-snap tolerance of change 2)
  3. disturbed episodes dropped at random (fixed seed) until normal episodes >= 50 % of the kept episodes
The file is read by tools/jcr/data_gate.py and tools/jcr/train.py (--select)."""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np

DT, V_MAX, A_MAX, DQ_MAX = 0.05, 0.08, 0.32, 0.04


def label_ok(s) -> bool:
    P = np.vstack([s["p_cmd"], s["chunk"]])
    vel = np.diff(P, axis=0) / DT
    if np.linalg.norm(vel, axis=1).max() > V_MAX + 1e-6:
        return False
    a = np.linalg.norm(np.diff(np.vstack([s["v"], vel]), axis=0), axis=1) / DT
    return bool(a.max() <= A_MAX * 1.01)


def samples_path(d):
    sp = os.path.join(d, "samples_r3.jsonl")
    return sp if os.path.exists(sp) else os.path.join(d, "samples.jsonl")


def load(path):
    if not path:
        return None
    return json.load(open(path))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    eps, ex_joint, bad_samples = [], {}, {}
    for ej in sorted(glob.glob(os.path.join(a.data, "*", "s*", "ep.json"))):
        d = os.path.dirname(ej)
        e = json.load(open(ej))
        q = np.array([json.loads(x)["q"] for x in open(os.path.join(d, "ticks.jsonl"))])
        dq = float(np.abs(np.diff(q, axis=0)).max()) if len(q) > 1 else 0.0
        if dq > DQ_MAX + 1e-9:
            ex_joint[d] = round(dq, 4)
            continue
        bad = [s["k"] for s in map(json.loads, open(samples_path(d))) if not label_ok(s)]
        if bad:
            bad_samples[d] = bad
        eps.append((d, bool(e["plan"]["normal"])))
    nrm = [d for d, n in eps if n]
    dis = [d for d, n in eps if not n]
    rng = np.random.default_rng(a.seed)
    n_drop = max(0, len(dis) - len(nrm))
    drop = sorted(rng.choice(dis, n_drop, replace=False).tolist()) if n_drop else []
    out = {"exclude_episodes": {**{d: f"joint_step {v} rad" for d, v in ex_joint.items()},
                                **{d: "composition (disturbed > normal)" for d in drop}},
           "exclude_samples": bad_samples,
           "counts": {"episodes_in": len(eps) + len(ex_joint), "joint_excluded": len(ex_joint),
                      "composition_excluded": len(drop), "kept": len(eps) - len(drop), "normal_kept": len(nrm),
                      "bad_label_samples": sum(map(len, bad_samples.values()))}}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out["counts"]))


if __name__ == "__main__":
    main()
