"""T14 outcome-based labels (E §2A.3). Isaac only (pod): python.sh -m harvest.cli_label ...

  selfcheck --seeds 0,1,2 --out DIR [--stride 1]   DEV P0 episodes: is the oracle answer in the best set (>= 95 %)?
  label --pool DIR --seeds 2000-2039               label every decision snapshot of the pool (no frames)

Questions: dir_xy, dir_z, mag_coarse (D-zoom), target, phase (H-plan), fine_dir (H-plan, only near contact).
Labels are per option_key (never per shown name): labels/ep<seed>.jsonl, one line per (snapshot, question).
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from .cli_pool import _seeds, _utc, attach_oracle, run_snapshot_episode
from .sim import labeler as L
from .sim import snapshot as S

ORACLE_KEY = {"dir_xy": "dir_xy", "dir_z": "dir_z", "mag_coarse": "mag_coarse", "target": "target",
              "phase": "phase_choice", "fine_dir": "fine_dir"}


def questions_for(oracle: dict) -> list[str]:
    qs = ["dir_xy", "dir_z", "mag_coarse", "target", "phase"]
    if oracle.get("near_contact"):
        qs.append("fine_dir")
    return qs


def label_snapshot(lab, snap: dict, present) -> list[dict]:
    rows = []
    for q in questions_for(snap["oracle"]):
        t0 = time.perf_counter()
        r = lab.label(snap, q, L.option_keys(q, present))
        ok = snap["oracle"][ORACLE_KEY[q]]
        rows.append({"key": snap["key"], "question": q, "best": sorted(r["best"]), "scores": r["scores"],
                     "oracle_key": ok, "oracle_in_best": ok in r["best"], "n_best": len(r["best"]),
                     "n_options": len(r["scores"]),
                     "outcomes": {k: {x: o[x] for x in ("success", "fail", "t_success", "t_fail", "phase", "dist_m",
                                                        "checkpoints", "sim_s")}
                                  for k, o in r["outcomes"].items()},
                     "wall_s": round(time.perf_counter() - t0, 2)})
    return rows


def selfcheck(seeds, out: str, stride: int, ks=None):
    from .sim.scene import make_env
    os.makedirs(out, exist_ok=True)
    env = make_env(seeds[0], headless=True, cameras=(), depth=False)
    lab = L.Labeler(env)
    path = f"{out}/selfcheck.jsonl"
    for seed in seeds:
        if seed not in S.DEV_SEEDS:
            raise SystemExit("selfcheck: DEV seeds only")
        res = run_snapshot_episode(env, seed, "P0")
        attach_oracle(res)
        for rec, s in res["snaps"][::stride]:
            if rec["oracle"] is None or (ks and rec["k"] not in ks):
                continue
            snap = {"key": f"dev{seed}_k{rec['k']}", "state": s, "oracle": rec["oracle"]}
            for row in label_snapshot(lab, snap, rec["present"]):
                row.update(seed=seed, k=rec["k"], t=rec["t"], phase=rec["phase"])
                print("LAB " + json.dumps({k: row[k] for k in ("seed", "k", "phase", "question", "oracle_key",
                                                              "best", "oracle_in_best", "wall_s")}), flush=True)
                with open(path, "a") as f:
                    f.write(json.dumps(S._jsonable(row)) + "\n")
        lab.cache.clear()
    print("SELFCHECK_DONE " + json.dumps({"rollouts": lab.n_rollouts, "sim_s": round(lab.sim_s, 1),
                                          "utc": _utc()}), flush=True)


def label_pool(pool_dir: str, seeds):
    from .sim.scene import make_env
    os.makedirs(f"{pool_dir}/labels", exist_ok=True)
    env = lab = None
    for seed in seeds:
        dst = f"{pool_dir}/labels/ep{seed}.jsonl"
        if os.path.exists(dst + ".done"):
            continue
        lines = [json.loads(x) for x in open(f"{pool_dir}/ep{seed}.jsonl")]
        arrays = np.load(f"{pool_dir}/ep{seed}.npz")
        if env is None:
            env = make_env(seed, headless=True, cameras=(), depth=False)
            lab = L.Labeler(env)
        t0, n0, s0 = time.perf_counter(), lab.n_rollouts, lab.sim_s
        with open(dst, "w") as f:
            for i, x in enumerate(lines):
                if not x["decision"]:
                    continue
                snap = {"key": f"ep{seed}_k{x['k']}", "state": S.unpack_state(arrays, i, x["state"]),
                        "oracle": x["oracle"]}
                for row in label_snapshot(lab, snap, x["state"]["present"]):
                    row.update(seed=seed, k=x["k"], t=x["t"], phase=x["phase"], split=x["split"], kind=x["kind"])
                    f.write(json.dumps(S._jsonable(row)) + "\n")
        lab.cache.clear()
        info = {"seed": seed, "wall_s": round(time.perf_counter() - t0, 1), "rollouts": lab.n_rollouts - n0,
                "sim_s": round(lab.sim_s - s0, 1), "utc": _utc()}
        with open(dst + ".done", "w") as f:
            json.dump(info, f)
        print("LABELED " + json.dumps(info), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["selfcheck", "label"])
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--out", default="/data/juhyoung_qdd/data/pool/selfcheck")
    ap.add_argument("--pool", default="/data/juhyoung_qdd/data/pool")
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--ks", default="", help="smoke: only these snapshot indices")
    a = ap.parse_args()
    seeds = _seeds(a.seeds)
    if a.mode == "selfcheck":
        selfcheck(seeds, a.out, a.stride, [int(x) for x in a.ks.split(",") if x])
    else:
        label_pool(a.pool, seeds)
    os._exit(0)


if __name__ == "__main__":
    main()
