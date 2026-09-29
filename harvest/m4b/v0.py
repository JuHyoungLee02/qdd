"""V0: the R1 explicit-perception pipeline (SAM 3.1 -> renderer depth -> 3D centroids -> code predicates) run on
FI-DEV frames (pod, venv_sam3). Same detection names (r1/out/phrases.json, frozen), fusion, tracker and predicate
code as harvest.perception.run_r1 eval (v2 gripper-contact rule = current state.py).

  python -m harvest.m4b.v0 --fi ROOT --seeds 15-29 --out FILE
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from . import spec as FS


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fi", default="/data/harvest/m4b/fidev")
    ap.add_argument("--seeds", default="15-29")
    ap.add_argument("--phrases", default="/data/harvest/r1/out")
    ap.add_argument("--out", required=True)
    ap.add_argument("--conds", default="all")
    a = ap.parse_args(argv)
    conds = FS.CONDITIONS if a.conds == "all" else tuple(a.conds.split(","))
    from ..perception.fuse import Tracker, fuse
    from ..perception.run_r1 import HEAD, WRIST, _cam_det, _img, _intr, _lines, load_phrases
    from ..perception.seg import Sam31Image
    from ..perception.state import est_line
    from ..predicates import PredicateState

    lo, hi = (int(x) for x in a.seeds.split("-"))
    Ks = _intr()
    phrases = load_phrases(a.phrases)
    sam = Sam31Image()
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(x)["ep"] for x in open(a.out)}
    fo = open(a.out, "a")
    for cond in conds:
        for seed in range(lo, hi + 1):
            FS.check_fi_seed(seed)
            ep = f"fi/{cond}/{seed}"
            root = f"{a.fi}/{cond}"
            if ep in done or not os.path.exists(f"{root}/ep{seed}.fi.json"):
                continue
            z = np.load(f"{root}/ep{seed}.r1.npz")
            lines = _lines(f"{root}/ep{seed}.jsonl")
            assert list(z["k"]) == [ln["k"] for ln in lines]
            tr, ps = Tracker(), PredicateState()
            rows = []
            for i, ln in enumerate(lines):
                present = ln["state"]["present"]
                segs, lat = {}, 0.0
                depth, poses = {}, {}
                for cam in (HEAD, WRIST):
                    depth[cam] = z[f"depth_{cam}"][i].astype(np.float32)
                    poses[cam] = (z[f"campos_{cam}"][i], z[f"camR_{cam}"][i])
                    segs[cam], tm = sam.segment(_img(root, ln["images"][cam]), [phrases[k] for k in present])
                    lat += tm["encode_ms"] + tm["ground_ms"]
                est = {}
                for k in present:
                    per = {cam: _cam_det(cam, segs[cam][phrases[k]], depth[cam], Ks[cam], *poses[cam])[0]
                           for cam in (HEAD, WRIST)}
                    est[k] = tr.update(k, fuse(per[HEAD], per[WRIST]))
                e = est_line(ln, est, ps)
                p = e["pred"]
                test = FS.truth(p, False)
                test["contact_stall"] = None  # V0 has no collision measurement
                rows.append({"key": f"{ep}/{ln['k']}", "pred": test, "sam_ms": lat})
            fo.write(json.dumps({"ep": ep, "rows": rows}) + "\n")
            fo.flush()
            print("EP", ep, len(rows), flush=True)


if __name__ == "__main__":
    main()
