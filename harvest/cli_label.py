"""T14 outcome-based labels (E §2A.3). Isaac only (pod): python.sh -m harvest.cli_label ...

  selfcheck --seeds 0-9 [--kinds P0,P1,P2] --out DIR   DEV episodes, all prereg candidate rules (prereg_labeler.md)
  summarize --out DIR                                   oracle-in-best / discrimination per rule -> chosen rule
  label --pool DIR --seeds 2000-2039 --rule R           label every decision snapshot of the pool (no frames)

Questions: dir_xy, dir_z, mag_coarse (D-zoom), target, phase (H-plan), fine_dir (H-plan, only near contact).
Labels are per option_key (never per shown name). Every row keeps the raw rollout outcomes and the best set under
every candidate rule (best_by_rule); `best` is the selected rule's.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import numpy as np

from .cli_pool import _seeds, _utc, attach_oracle, run_snapshot_episode
from .sim import labeler as L
from .sim import snapshot as S

ORACLE_KEY = {"dir_xy": "dir_xy", "dir_z": "dir_z", "mag_coarse": "mag_coarse", "target": "target",
              "phase": "phase_choice", "fine_dir": "fine_dir"}
OUT_FIELDS = ("success", "fail", "t_success", "t_fail", "phase", "dist_m", "checkpoints", "sim_s", "fail_stage")


def questions_for(oracle: dict) -> list[str]:
    qs = ["dir_xy", "dir_z", "mag_coarse", "target", "phase"]
    if oracle.get("near_contact"):
        qs.append("fine_dir")
    return qs


def label_snapshot(lab, snap: dict, present, rule: str = "plan") -> list[dict]:
    from .sim.snapshot import PHASE_ORDER
    rows = []
    for q in questions_for(snap["oracle"]):
        t0 = time.perf_counter()
        r = lab.label(snap, q, L.option_keys(q, present))
        ok = snap["oracle"][ORACLE_KEY[q]]
        outs = r["outcomes"]
        by_rule = {ru: sorted(L.rule_best(outs, ru, PHASE_ORDER)) for ru in L.RULES}
        rows.append({"key": snap["key"], "question": q, "rule": rule or None, "best": by_rule.get(rule),
                     "best_by_rule": by_rule, "scores_plan": r["scores"], "oracle_key": ok,
                     "oracle_in_best": {ru: ok in b for ru, b in by_rule.items()}, "n_options": len(outs),
                     "outcomes": {k: {x: o.get(x) for x in OUT_FIELDS} for k, o in outs.items()},
                     "replay_maxabs": max([o.get("replay_maxabs") or 0.0 for o in outs.values()]),
                     "replay_obj_mm": max([o.get("replay_obj_mm") or 0.0 for o in outs.values()]),
                     "replay_jpos_rad": max([o.get("replay_jpos_rad") or 0.0 for o in outs.values()]),
                     "wall_s": round(time.perf_counter() - t0, 2)})
    return rows


def selfcheck(seeds, kinds, out: str, ks=None):
    """prereg_labeler.md: DEV 0-29 x P0-P2, every decision snapshot (chosen as in the pool), all candidate rules."""
    from .cli_pool import canonical_prefix, choose_decisions
    from .sim.scene import make_env
    os.makedirs(out, exist_ok=True)
    from .cli_pool import warmup
    env = make_env(seeds[0], headless=True, cameras=(), depth=False)
    warmup(env)
    lab = L.Labeler(env)
    for seed in seeds:
        if seed not in S.DEV_SEEDS:
            raise SystemExit("selfcheck: DEV seeds only")
        for kind in kinds:
            path = f"{out}/dev{seed}_{kind}.jsonl"
            if os.path.exists(path + ".done"):
                continue
            t0, n0 = time.perf_counter(), lab.n_rollouts
            canonical_prefix(env)
            res = run_snapshot_episode(env, seed, kind)
            attach_oracle(res)
            _, chosen = choose_decisions(res)
            with open(path, "w") as f:
                for i, (rec, s) in enumerate(res["snaps"]):
                    if i not in chosen or (ks and rec["k"] not in ks):
                        continue
                    snap = {"key": f"dev{seed}{kind}_k{rec['k']}", "state": s, "oracle": rec["oracle"],
                            "replay": {"seed": seed, "kind": kind, "k": rec["k"]}}
                    for row in label_snapshot(lab, snap, rec["present"]):
                        row.update(seed=seed, kind=kind, k=rec["k"], t=rec["t"], phase=rec["phase"],
                                   oversampled=chosen[i][0], w_natural=chosen[i][1],
                                   episode_success=res["success"])
                        f.write(json.dumps(S._jsonable(row)) + "\n")
            lab.cache.clear()
            info = {"seed": seed, "kind": kind, "success": res["success"], "rollouts": lab.n_rollouts - n0,
                    "sim_s": round(lab.sim_s, 1), "wall_s": round(time.perf_counter() - t0, 1), "utc": _utc()}
            with open(path + ".done", "w") as f:
                json.dump(info, f)
            print("SELF " + json.dumps(info), flush=True)


def summarize(out: str) -> dict:
    """Per rule: oracle-in-best rate and discrimination (mean over questions of 1 - |best|/|options|)."""
    rows = [json.loads(x) for p in sorted(glob.glob(f"{out}/*.jsonl")) for x in open(p)]
    stats, per_q = {}, {}
    qs = sorted({r["question"] for r in rows})
    for ru in L.RULES:
        orc = [r["oracle_in_best"][ru] for r in rows]
        disc = [1 - len(r["best_by_rule"][ru]) / r["n_options"] for r in rows]
        stats[ru] = (float(np.mean(orc)), float(np.mean(disc)))
        for q in qs:
            sub = [r for r in rows if r["question"] == q]
            per_q.setdefault(ru, {})[q] = [round(float(np.mean([r["oracle_in_best"][ru] for r in sub])), 4),
                                           round(float(np.mean([1 - len(r["best_by_rule"][ru]) / r["n_options"]
                                                                for r in sub])), 4), len(sub)]
    chosen = L.select_rule(stats)
    res = {"n_rows": len(rows), "n_snapshots": len({r["key"] for r in rows}),
           "episodes": len({(r["seed"], r["kind"]) for r in rows}),
           "stats": {k: [round(a, 4), round(b, 4)] for k, (a, b) in stats.items()}, "per_question": per_q,
           "chosen": chosen, "utc": _utc()}
    print("SUMMARY " + json.dumps(res), flush=True)
    with open(f"{out}/summary.json", "w") as f:
        json.dump(res, f, indent=1)
    return res


def label_pool(pool_dir: str, seeds, rule: str):
    from .sim.scene import make_env
    if rule and rule not in L.RULES:
        raise SystemExit(f"--rule must be one of {L.RULES} (or empty: best set later by finalize)")
    os.makedirs(f"{pool_dir}/labels", exist_ok=True)
    env = lab = None
    for seed in seeds:
        dst = f"{pool_dir}/labels/ep{seed}.jsonl"
        if os.path.exists(dst + ".done"):
            continue
        try:  # several processes may share a seed list: first one to create the lock takes the episode
            os.close(os.open(dst + ".lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            continue
        lines = [json.loads(x) for x in open(f"{pool_dir}/ep{seed}.jsonl")]
        arrays = np.load(f"{pool_dir}/ep{seed}.npz")
        if env is None:
            from .cli_pool import warmup
            env = make_env(seed, headless=True, cameras=(), depth=False)
            warmup(env)
            lab = L.Labeler(env)
        t0, n0, s0 = time.perf_counter(), lab.n_rollouts, lab.sim_s
        with open(dst, "w") as f:
            for i, x in enumerate(lines):
                if not x["decision"]:
                    continue
                snap = {"key": f"ep{seed}_k{x['k']}", "state": S.unpack_state(arrays, i, x["state"]),
                        "oracle": x["oracle"], "replay": {"seed": seed, "kind": x["kind"], "k": x["k"]}}
                for row in label_snapshot(lab, snap, x["state"]["present"], rule):
                    row.update(seed=seed, k=x["k"], t=x["t"], phase=x["phase"], split=x["split"], kind=x["kind"],
                               oversampled=x["oversampled"], w_natural=x["w_natural"],
                               w_oversample=x["w_oversample"], ambiguous=x["ambiguous"])
                    f.write(json.dumps(S._jsonable(row)) + "\n")
        lab.cache.clear()
        info = {"seed": seed, "wall_s": round(time.perf_counter() - t0, 1), "rollouts": lab.n_rollouts - n0,
                "sim_s": round(lab.sim_s - s0, 1), "utc": _utc()}
        with open(dst + ".done", "w") as f:
            json.dump(info, f)
        print("LABELED " + json.dumps(info), flush=True)


def finalize(pool_dir: str, rule: str) -> dict:
    """Set `best` (and `rule`) of every pool label row from best_by_rule once the DEV self-check chose the rule."""
    if rule not in L.RULES:
        raise SystemExit(f"--rule must be one of {L.RULES}")
    n = 0
    for p in sorted(glob.glob(f"{pool_dir}/labels/ep*.jsonl")):
        rows = [json.loads(x) for x in open(p)]
        for r in rows:
            r["rule"], r["best"] = rule, r["best_by_rule"][rule]
        with open(p, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        n += len(rows)
    info = {"rule": rule, "rows": n, "utc": _utc()}
    print("FINAL " + json.dumps(info), flush=True)
    return info


def pool_summary(pool_dir: str) -> dict:
    """After finalize: per question, rows, mean |best| / |options|, oracle-in-best, how often each option_key is in
    the best set (natural-weighted with w_natural and as sampled), replay exactness, and time cost."""
    rows = [json.loads(x) for p in sorted(glob.glob(f"{pool_dir}/labels/ep*.jsonl")) for x in open(p)]
    done = [json.load(open(p)) for p in sorted(glob.glob(f"{pool_dir}/labels/ep*.jsonl.done"))]
    out = {"rows": len(rows), "snapshots": len({r["key"] for r in rows}), "episodes": len(done),
           "rule": sorted({r["rule"] for r in rows}), "questions": {}}
    for q in sorted({r["question"] for r in rows}):
        sub = [r for r in rows if r["question"] == q]
        w = np.array([r["w_natural"] or 0.0 for r in sub])
        keys = sorted({k for r in sub for k in r["outcomes"]})
        inb = {k: [k in r["best"] for r in sub] for k in keys}
        out["questions"][q] = {
            "rows": len(sub), "mean_best_frac": round(float(np.mean([len(r["best"]) / r["n_options"] for r in sub])), 4),
            "discrimination": round(float(np.mean([1 - len(r["best"]) / r["n_options"] for r in sub])), 4),
            "oracle_in_best": round(float(np.mean([r["oracle_key"] in r["best"] for r in sub])), 4),
            "in_best_sampled": {k: round(float(np.mean(v)), 4) for k, v in inb.items()},
            "in_best_natural": {k: round(float(np.sum(w * np.array(v)) / max(w.sum(), 1e-9)), 4) for k, v in inb.items()}}
    out["replay_max_obj_mm"] = max([r.get("replay_obj_mm") or 0.0 for r in rows] or [0.0])
    out["replay_max_state"] = max([r.get("replay_maxabs") or 0.0 for r in rows] or [0.0])
    out["replay_rows_over_1mm"] = sum((r.get("replay_obj_mm") or 0.0) > 1.0 for r in rows)
    out["wall_s_total"] = round(sum(d["wall_s"] for d in done), 1)
    out["sim_s_total"] = round(sum(d["sim_s"] for d in done), 1)
    out["rollouts_total"] = sum(d["rollouts"] for d in done)
    print("POOLSUM " + json.dumps(out), flush=True)
    with open(f"{pool_dir}/labels/summary.json", "w") as f:
        json.dump(out, f, indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["selfcheck", "summarize", "label", "finalize", "poolsum"])
    ap.add_argument("--seeds", default="0-29")
    ap.add_argument("--kinds", default="P0,P1,P2")
    ap.add_argument("--out", default="/data/harvest/data/pool/selfcheck")
    ap.add_argument("--pool", default="/data/harvest/data/pool")
    ap.add_argument("--rule", default="")
    ap.add_argument("--ks", default="", help="smoke: only these snapshot indices")
    a = ap.parse_args()
    if a.mode == "summarize":
        summarize(a.out)
        return
    if a.mode == "finalize":
        finalize(a.pool, a.rule)
        return
    if a.mode == "poolsum":
        pool_summary(a.pool)
        return
    seeds = _seeds(a.seeds)
    if a.mode == "selfcheck":
        kinds = a.kinds.split(",")
        if not set(kinds) <= set(S.POOL_KINDS):
            raise SystemExit("DEV perturbations P0-P2 only")
        selfcheck(seeds, kinds, a.out, [int(x) for x in a.ks.split(",") if x])
    else:
        label_pool(a.pool, seeds, a.rule)
    os._exit(0)


if __name__ == "__main__":
    main()
