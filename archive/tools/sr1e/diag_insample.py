"""E-SR1e design diagnostic D1 (docs/stage3/prereg_sr1e.md §0.3; outside any verdict): counterfactual adherence of an
existing checkpoint on TRAIN-split far snapshots (fitting) next to the val result (generalization).

tools/sr1d/sr1d_eval.py is run unchanged on a different snapshot list: its snapshot source (tools/sr0/sr0_eval.snapshots)
is replaced by N train samples of proxy stratum 'far' with a label dir_xy (numpy default_rng(sel_seed) over the sorted
keys). Each chosen snapshot is also tagged 'drawn' when the E-SR1d training run of --drawn-seed actually drew one of its
branch rows: the branch list order is harvest/train/sr1d.join_branches over read_branch_rows (sorted files), and the
draws are sr1c.with_branches' numpy RNG default_rng([seed, sr1c.SALT]).integers(0, n, n_branch(8, frac)) once per step.

  python tools/sr1e/diag_insample.py --n 400 --sel-seed 0 --branches DIR --drawn-seed S --steps 2000 --frac 0.5 \
      --tags OUT.tags.json -- <tools/sr1d/sr1d_eval.py arguments (--ckpt ... --meta ... --out ...)>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_HERE, "..", "..")
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402


def drawn_counts(branch_root: str, seed: int, steps: int, frac: float, batch: int = 8) -> dict:
    from harvest.train import sr1c
    from harvest.train.sr1d import key_of, read_branch_rows
    keys = [key_of(r["kind"], r["seed"], r["k"]) for r in read_branch_rows(branch_root)]
    rng = np.random.default_rng([int(seed), sr1c.SALT])
    nb = sr1c.n_branch(batch, frac)
    cnt = {}
    for _ in range(steps):
        for i in rng.integers(0, len(keys), size=nb):
            cnt[keys[i]] = cnt.get(keys[i], 0) + 1
    return {"n_rows": len(keys), "n_sources": len(set(keys)), "counts": cnt}


def main():
    argv = sys.argv[1:]
    cut = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--sel-seed", type=int, default=0)
    ap.add_argument("--branches", required=True)
    ap.add_argument("--drawn-seed", type=int, required=True)
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--frac", type=float, default=0.5)
    ap.add_argument("--tags", required=True)
    a = ap.parse_args(argv[:cut])
    rest = argv[cut + 1:]
    spec = importlib.util.spec_from_file_location("sr1d_eval", os.path.join(ROOT, "tools", "sr1d", "sr1d_eval.py"))
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    dc = drawn_counts(a.branches, a.drawn_seed, a.steps, a.frac)

    def train_far(ea):
        from harvest.train import stageb_train as TR
        meta = M.read_meta(ea.meta)
        _, _, tr, _ = TR._load_data(ea)
        cand = sorted((s["key"], s) for s in tr if meta[s["key"]]["stratum"] == "far"
                      and all(s["committed"].get(q) is not None for q in M.E0.JOY))
        idx = np.sort(np.random.default_rng(a.sel_seed).choice(len(cand), size=min(a.n, len(cand)), replace=False))
        chosen = [cand[i] for i in idx]
        tags = {k: dc["counts"].get(k, 0) for k, _ in chosen}
        json.dump({"n_cand": len(cand), "n": len(chosen), "sel_seed": a.sel_seed, "drawn_seed": a.drawn_seed,
                   "steps": a.steps, "frac": a.frac, "branch_rows": dc["n_rows"], "branch_sources": dc["n_sources"],
                   "sources_drawn": len(dc["counts"]), "draws": tags}, open(a.tags, "w"), indent=1)
        return chosen
    M.E0.snapshots = train_far
    M.main(rest)


if __name__ == "__main__":
    main()
