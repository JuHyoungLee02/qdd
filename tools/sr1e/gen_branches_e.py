"""E-SR1e branch generation (docs/stage3/prereg_sr1e.md §2): tools/sr1d/gen_branches.py run unchanged except three
module constants / hooks (CPU only, no simulator):
  --k K          forced decisions per snapshot (E-SR1d 4; 7 = every direction but the label, sr1c_branch.forced_decisions
                 draws K distinct of the 8 directions without the label, so K <= 7 when the label has a direction)
  --strata S     comma list of eligible proxy strata of TRAIN rows (E-SR1d 'far'; e.g. 'far,band')
  --salt SALT    RNG salt of the per-snapshot draws (E-SR1d 'sr1d-branch@v1')
Every kinematic check / threshold / IK setting is the E-SR1d one (sr1d_kin, gen_branches.plan_snapshot).
  python tools/sr1e/gen_branches_e.py --k 7 --strata far --salt sr1e-branch@v1 -- <tools/sr1d/gen_branches.py args>
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_HERE, "..", "..")
sys.path.insert(0, ROOT)


def load_gen():
    spec = importlib.util.spec_from_file_location("gen_branches", os.path.join(ROOT, "tools", "sr1d", "gen_branches.py"))
    G = importlib.util.module_from_spec(spec)
    sys.modules["gen_branches"] = G  # pool workers (fork) resolve run_part by this name
    spec.loader.exec_module(G)
    return G


def patch(G, k: int, strata: tuple, salt: str):
    if not 1 <= k <= 7:
        raise SystemExit("--k in 1..7")
    orig = G.plan_snapshot
    G.K, G.SALT = k, salt

    def plan_snapshot(chain, limits, row, meta, ds, rng, K=None):
        return orig(chain, limits, row, meta, ds, rng, K=G.K if K is None else K)

    def eligible(meta: dict, mode: str) -> bool:
        return meta["split"] == "train" and meta["stratum"] in strata
    G.plan_snapshot, G.eligible = plan_snapshot, eligible
    return G


def main():
    argv = sys.argv[1:]
    cut = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--strata", required=True)
    ap.add_argument("--salt", required=True)
    a = ap.parse_args(argv[:cut])
    G = patch(load_gen(), a.k, tuple(x for x in a.strata.split(",") if x), a.salt)
    rest = argv[cut + 1:]
    if "--mode" not in rest:
        rest += ["--mode", "all" if a.strata != "far" else "far"]  # recorded in stats.json only
    G.main(rest)


if __name__ == "__main__":
    main()
