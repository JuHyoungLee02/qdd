"""E-SR1e in-run gates (docs/stage3/prereg_sr1e.md §0.5): tools/sr1d/sr1d_gate.py (imported, not modified) with the
E-SR1e allowances. Each subcommand prints a JSON line with 'pass' and exits 1 on failure.
  gkin  --stats BRANCH_STATS --strata S            = E-SR1d G-kin (same thresholds) on the E-SR1e branch set
  g0    --log TRAIN_STDOUT --stats BRANCH_STATS --nb N   branch join = generated rows, missing 0, n_branch == N each step
  g1    --eval C0_EVAL --sr0 SR0_JSONL             = E-SR1d G1 (C0 re-evaluation reproduces E-SR0)
  g2    --log TRAIN_LOG --max-s S                  loop time <= S, finite losses
  cfg   --log TRAIN_LOG --ref REF_LOG              training args = the reference run's args except the E-SR1d / E-SR1e
                                                   options, names, max_steps, save_every and sr1e_branch_chunk
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sr1d_gate", os.path.join(_HERE, "..", "sr1d", "sr1d_gate.py"))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

CFG_ALLOWED_E = set(G.CFG_ALLOWED) | {"max_steps", "save_every", "sr1e_branch_chunk"}


def gate_g0(a):
    recs = G._log(a.log)
    t = json.load(open(a.stats))["total"]
    j = [r for r in recs if r.get("event") == "sr1d_branches"]
    tr = [r for r in recs if r.get("event") == "train"]
    nb = sorted({r.get("n_branch") for r in tr})
    ok = bool(j) and j[-1]["joined"] == t["branches"] and j[-1]["missing"] == 0 and nb == [a.nb] and len(tr) > 0
    return G._out("g0", ok, join=j[-1] if j else None, branches=t["branches"], n_branch=nb, steps=len(tr))


def gate_cfg(a):
    G.CFG_ALLOWED = CFG_ALLOWED_E
    return G.gate_cfg(a)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("gkin")
    p.add_argument("--stats", required=True)
    p.add_argument("--strata", required=True)
    p = sub.add_parser("g0")
    p.add_argument("--log", required=True)
    p.add_argument("--stats", required=True)
    p.add_argument("--nb", type=int, required=True)
    p = sub.add_parser("g1")
    p.add_argument("--eval", required=True)
    p.add_argument("--sr0", required=True)
    p = sub.add_parser("g2")
    p.add_argument("--log", required=True)
    p.add_argument("--max-s", type=float, required=True)
    p = sub.add_parser("cfg")
    p.add_argument("--log", required=True)
    p.add_argument("--ref", required=True)
    a = ap.parse_args(argv)
    rc = {"gkin": G.gate_gkin, "g0": gate_g0, "g1": G.gate_g1, "g2": G.gate_g2, "cfg": gate_cfg}[a.cmd](a)
    sys.exit(rc)


if __name__ == "__main__":
    main()
