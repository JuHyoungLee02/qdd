"""Offline change-3 relabel of recorded JCR data (prereg_jcr1.md change 3): every sample already stores the state the
truth rules need (commanded TCP p_cmd, its velocity v, the true point goal_true -- moved with the object at that
tick --, the received command goal_cmd, adapter kappa, command age, stop), so the new labels are recomputed without
re-running Isaac:
  labels = {P: straight to the true point (JCR's own label, rules B / C), A / A1 / A2: hard clip 3 / 1 / 2 cm}
  chunk = labels[P];  cmd_mismatch = |goal_true - goal_cmd| > 3 cm (one definition for every rule)
Writes <episode>/samples_r3.jsonl next to samples.jsonl (the recording is never modified); the training loader prefers
samples_r3.jsonl. Episodes still being written (no ep.json) are skipped.
  python tools/jcr/relabel.py --data /data/harvest/out/jcr/d1 [--force]"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.jcr import truth as T  # noqa: E402
from harvest.jcr.exec_truth import LABELS  # noqa: E402


def relabel(s: dict) -> dict:
    out = dict(s)
    lab = {m: T.mode_chunk(m, s["p_cmd"], s["v"], s["goal_true"], s["goal_cmd"], float(s.get("kappa", 0.9)),
                           float(s.get("cmd_age", 0.0)), stop=bool(s.get("stop"))).round(6).tolist() for m in LABELS}
    an = set(s.get("anomaly", ())) - {"cmd_mismatch"}
    if T.mismatch(s["goal_true"], s["goal_cmd"]):
        an.add("cmd_mismatch")
    out.update(labels=lab, chunk=lab["P"], anomaly=sorted(an), label_rule=3)
    out.pop("c_star", None)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    n_ep = n_s = 0
    for ej in sorted(glob.glob(os.path.join(a.data, "*", "s*", "ep.json"))):
        d = os.path.dirname(ej)
        dst = os.path.join(d, "samples_r3.jsonl")
        if os.path.exists(dst) and not a.force:
            continue
        if json.load(open(ej)).get("label_rule") == 3:  # recorded with the change-3 code: labels already right
            continue
        rows = [relabel(json.loads(x)) for x in open(os.path.join(d, "samples.jsonl"))]
        tmp = dst + ".tmp"
        with open(tmp, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        os.replace(tmp, dst)
        n_ep += 1
        n_s += len(rows)
    print(json.dumps({"episodes": n_ep, "samples": n_s}))


if __name__ == "__main__":
    main()
