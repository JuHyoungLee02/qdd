"""Standard -> random (-> dr) generalization drop, RD (EVAL §4.2, canon §52 "RD 변화", §55 next (1)) -- one command.

  python -m harvest.eval.rd --model <merged | adapter | zero-shot> --out DIR \
      --variants standard=/data/harvest/data/jsel_dev,random=/data/harvest/data/gen_dev/random,dr=.../gen_dev/dr \
      --split dev [--episodes N] [--compare OTHER_RD_OUT] \
      [--closed --seeds 0-4 --conditions C5 --isaac-gpu 1 [--max-seconds 60] [--astra mock]]

Offline part: every snapshot of each variant is asked once (A0, S1 1 mm, §59 lead) and scored against that variant's
labels_v2 (or --truth outcome:<rule>). Items are paired by (kind, seed, k, question) -- the same DEV layout seed and
snapshot in the standard and the varied scene -- so the drop A_std - A_var has a paired episode-cluster CI (the
stageA_generalize tool, generalized to any model); relative RD = 1 - A_var / A_std, plus the unpaired difference,
the per-variant majority baseline, per question / per kind. --compare DIR (another rd output, e.g. zero-shot) gives
the difference of drops dRD = (A_std - A_var)_this - (A_std - A_var)_other on items present in both.
--closed: the closed-loop RD through the R5 runtime (harvest.eval.closed) on paired layout seeds: success rates per
variant and RD = 1 - SR_var / SR_std with a paired bootstrap over seeds.
Output <out>/rd.json, rd.md, items.jsonl, <variant>/calls.jsonl.
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import time
from collections import Counter, defaultdict
from types import SimpleNamespace

import numpy as np

from ..analysis.stats import N_BOOT
from .e05 import diff_ci, mean_ci


def expand_dirs(d: str) -> list:
    """A folder with ep*.jsonl, or a DEV root with kind subfolders P0/P1/P2."""
    if glob.glob(os.path.join(d, "ep*.jsonl")):
        return [d]
    subs = [os.path.join(d, k) for k in ("P0", "P1", "P2") if glob.glob(os.path.join(d, k, "ep*.jsonl"))]
    return subs


def _by(items, keys):
    b = defaultdict(list)
    for k in keys:
        b[items[k]["cluster"]].append(items[k]["correct"])
    return b


def _acc(items, keys, n_boot):
    return mean_ci(_by(items, keys), n_boot)


def _slices(keys):
    qs = sorted({k[3] for k in keys})
    return [("pooled", keys)] + [(q, [k for k in keys if k[3] == q]) for q in qs]


def majority(items, n_boot: int = N_BOOT) -> dict:
    """Always-pick-the-most-frequent label per question (that variant's own labels)."""
    c = defaultdict(Counter)
    for k, v in items.items():
        c[k[3]][v["y"]] += 1
    lab = {q: x.most_common(1)[0][0] for q, x in c.items()}
    b = defaultdict(list)
    for k, v in items.items():
        b[v["cluster"]].append(int(v["y"] == lab[k[3]]))
    return {"labels": lab, "pooled": mean_ci(b, n_boot)}


def offline_rd(V: dict, n_boot: int = N_BOOT) -> dict:
    """V: {variant: {(kind, seed, k, q): {cluster, correct, key, y}}}; 'standard' is the reference."""
    out = {"A": {}, "majority": {}, "RD": {}}
    for v, I in V.items():
        ks = sorted(I)
        out["A"][v] = {n: _acc(I, kk, n_boot) for n, kk in _slices(ks)}
        out["A"][v]["per_kind"] = {kind: _acc(I, [k for k in ks if k[0] == kind], n_boot)
                                   for kind in sorted({k[0] for k in ks})}
        out["A"][v]["choices"] = {q: dict(Counter(I[k]["key"] for k in ks if k[3] == q).most_common())
                                  for q in sorted({k[3] for k in ks})}
        out["majority"][v] = majority(I, n_boot)
    S = V.get("standard")
    if S is None:
        return out
    for v, I in V.items():
        if v == "standard":
            continue
        ks = sorted(set(S) & set(I))
        res = {"per_question": {}}
        for n, kk in _slices(ks):
            d = defaultdict(list)
            for k in kk:
                d[S[k]["cluster"]].append(S[k]["correct"] - I[k]["correct"])
            a_s = float(np.mean([S[k]["correct"] for k in kk])) if kk else None
            a_v = float(np.mean([I[k]["correct"] for k in kk])) if kk else None
            r = {"drop": mean_ci(d, n_boot), "n_paired": len(kk), "A_std": a_s, "A_var": a_v,
                 "relative": round(1 - a_v / a_s, 4) if kk and a_s else None}
            if n == "pooled":
                r["unpaired"] = diff_ci(_by(S, sorted(S)), _by(I, sorted(I)), n_boot)
                res["pooled"] = r
            else:
                res["per_question"][n] = r
        out["RD"][v] = res
    return out


def drd(A: dict, B: dict, variant: str, n_boot: int = N_BOOT) -> dict:
    """(S_A - V_A) - (S_B - V_B) per item present in all four runs, episode-cluster CI."""
    SA, VA, SB, VB = A["standard"], A[variant], B["standard"], B[variant]
    ks = sorted(set(SA) & set(VA) & set(SB) & set(VB))
    d = defaultdict(list)
    for k in ks:
        d[SA[k]["cluster"]].append((SA[k]["correct"] - VA[k]["correct"]) - (SB[k]["correct"] - VB[k]["correct"]))
    return mean_ci(d, n_boot)


def items_from(eps, done, truth, questions) -> dict:
    out = {}
    for ep in eps:
        for ln in ep["lines"]:
            r = done.get((ep["dir"], ep["seed"], ln["k"], "A0#0"))
            t = truth.get((ep["kind"], ep["seed"], ln["k"]))
            if r is None or t is None:
                continue
            for q in questions:
                if q not in t:
                    continue
                a = r["answers"].get(q)
                key = a["key"] if a else None  # failed call / missing answer = wrong (prereg jevl_acc)
                out[(ep["kind"], ep["seed"], ln["k"], q)] = {"cluster": (ep["kind"], ep["seed"]),
                                                            "correct": int(key is not None and key in t[q]),
                                                            "key": key, "y": sorted(t[q])[0]}
    return out


def _args(argv):
    ap = argparse.ArgumentParser(prog="python -m harvest.eval.rd", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", required=True, help="name=dir,... (standard is the reference)")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--episodes", type=int, default=0)
    ap.add_argument("--seeds", default="")
    ap.add_argument("--truth", default="labels_v2")
    ap.add_argument("--outcome-dirs", default="")
    ap.add_argument("--compare", default="")
    ap.add_argument("--layout", default="auto")
    ap.add_argument("--mode", default="lead")
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--gpu", default="3")
    ap.add_argument("--gpu-util", type=float, default=0.30)
    ap.add_argument("--url", default="")
    ap.add_argument("--served-name", default="")
    ap.add_argument("--n-boot", type=int, default=N_BOOT, help="bootstrap draws (E §1.7 / EVAL §4.2: 10,000)")
    ap.add_argument("--no-offline", action="store_true")
    ap.add_argument("--closed", action="store_true")
    ap.add_argument("--conditions", default="C5")
    ap.add_argument("--closed-seeds", default="0")
    ap.add_argument("--isaac-gpu", default="1")
    ap.add_argument("--max-seconds", type=float, default=60.0)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--astra", default="mock")
    ap.add_argument("--parallel", action="store_true")
    return ap.parse_args(argv)


def _md(res, meta) -> str:
    from .common import ci_str, md_table
    L = [f"# RD — {meta['model']['spec']}", "",
         f"- utc {meta['utc']}, git {meta['git']}, code_sha {meta['code_sha']}, model fingerprint "
         f"{meta['model'].get('fingerprint')}, prompt_config {meta['prompt_config']['sha']} (layout {meta['layout']}), "
         f"split {meta['split']}, truth {meta['truth']}, runtime {meta['runtime_s']}"]
    off = res.get("offline")
    if off:
        L += ["", "## Accuracy per variant", "",
              md_table(["variant", "A [95% CI]", "n", "majority", "per kind"],
                       [[v, ci_str(a["pooled"]), a["pooled"]["n"], ci_str(off["majority"][v]["pooled"]),
                         ", ".join(f"{k} {x['mean']}" for k, x in a["per_kind"].items())] for v, a in off["A"].items()]),
              "", "## Offline RD (paired items)", "",
              md_table(["variant", "slice", "A_std", "A_var", "drop [95% CI]", "relative RD", "n paired"],
                       [[v, n, x["A_std"], x["A_var"], ci_str(x["drop"]), x["relative"], x["n_paired"]]
                        for v, r in off["RD"].items()
                        for n, x in [("pooled", r["pooled"])] + sorted(r["per_question"].items())])]
        if res.get("dRD"):
            L += ["", f"## dRD vs {meta['compare']}", "",
                  md_table(["variant", "dRD [95% CI]", "n"], [[v, ci_str(x), x["n"]] for v, x in res["dRD"].items()])]
    if res.get("closed"):
        from .closed import _md as cmd
        L += ["", cmd(res["closed"]["result"], res["closed"]["meta"]).replace("# Closed loop", "## Closed loop")]
    return "\n".join(L)


def main(argv=None):
    from . import common as C
    from .e05 import _collect, parse_seeds
    from .splits import check_split
    a = _args(argv)
    check_split(a.split)
    t0 = time.monotonic()
    os.makedirs(a.out, exist_ok=True)
    info = C.ensure_merged(C.resolve_model(a.model), a.out)
    pc = C.training_prompt_config(info["path"]) if info["kind"] != "mock" else None
    layout = C.default_layout(pc) if a.layout == "auto" else a.layout
    vd = dict(x.split("=", 1) for x in a.variants.split(",") if x)
    if "standard" not in vd:
        raise SystemExit("--variants needs standard=<dir>")
    res, t_calls = {}, 0.0
    V, seeds_used = {}, {}
    if not a.no_offline:
        eps = {v: C.load_episodes(expand_dirs(d), a.split, a.episodes, parse_seeds(a.seeds)) for v, d in vd.items()}
        od = [d for d in a.outcome_dirs.split(",") if d]
        with C.Server(info, a.gpu, a.out, a.url, a.served_name, a.gpu_util) as srv:
            for v, E in eps.items():
                asker = C.MockAsker() if info["kind"] == "mock" else C.Asker(srv.url, srv.name, layout, a.mode)
                ns = SimpleNamespace(same_k=1, variants="A0", blocks=0, floor_n=0, conc=a.conc)
                vout = os.path.join(a.out, v)
                os.makedirs(vout, exist_ok=True)

                async def go(asker=asker, E=E, vout=vout, ns=ns):
                    try:
                        return await _collect(asker, E, ns, vout)
                    finally:
                        await asker.close()
                t1 = time.monotonic()
                done = asyncio.run(go())
                t_calls += time.monotonic() - t1
                V[v] = items_from(E, done, C.load_truth(E, a.truth, od), C.QUESTIONS)
                seeds_used[v] = sorted({(e["kind"], e["seed"]) for e in E})
            t_ready = getattr(srv, "t_ready", 0.0)
        res["offline"] = offline_rd(V, a.n_boot)
        with open(os.path.join(a.out, "items.jsonl"), "w", encoding="utf-8") as f:
            for v, I in V.items():
                for k, x in I.items():
                    f.write(json.dumps({"variant": v, "kind": k[0], "seed": k[1], "k": k[2], "q": k[3], **x}) + "\n")
        if a.compare:
            B = defaultdict(dict)
            for x in open(os.path.join(a.compare, "items.jsonl"), encoding="utf-8"):
                r = json.loads(x)
                B[r["variant"]][(r["kind"], r["seed"], r["k"], r["q"])] = {"cluster": tuple(r["cluster"]),
                                                                           "correct": r["correct"]}
            res["dRD"] = {v: drd(V, B, v, a.n_boot) for v in V if v != "standard" and v in B and "standard" in B}
    else:
        t_ready = 0.0
    if a.closed:
        from .closed import _args as cargs, run as crun
        cl = cargs(["--model", a.model, "--out", os.path.join(a.out, "closed"), "--split", a.split,
                    "--seeds", a.closed_seeds, "--variants", ",".join(vd), "--conditions", a.conditions,
                    "--isaac-gpu", a.isaac_gpu, "--gpu", a.gpu, "--max-seconds", str(a.max_seconds),
                    "--epochs", str(a.epochs), "--astra", a.astra, "--layout", layout, "--mode", a.mode,
                    "--n-boot", str(a.n_boot)] + (["--url", a.url, "--served-name", a.served_name] if a.url else [])
                   + (["--parallel"] if a.parallel else []))
        res["closed"] = crun(cl)
    meta = C.run_meta("rd", info, {
        "split": a.split, "variants": vd, "seeds": {v: [list(x) for x in s] for v, s in seeds_used.items()},
        "truth": a.truth, "layout": layout, "mode": a.mode, "prompt_config": C.prompt_config_eval(layout),
        "compare": a.compare or None,
        "bootstrap": C.bootstrap_meta(a.n_boot, "episode (kind, layout seed); standard / variant items paired by "
                                                "(kind, seed, k, question)"),
        "runtime_s": {"total": round(time.monotonic() - t0, 1), "calls": round(t_calls, 1),
                      "vllm_ready": round(t_ready, 1)}})
    C.write_outputs(a.out, "rd", {"meta": meta, "result": res}, _md(res, meta))
    brief = {v: r["pooled"]["drop"] for v, r in res.get("offline", {}).get("RD", {}).items()}
    print("RD_DONE " + json.dumps({"out": a.out, "drop": brief, "runtime_s": meta["runtime_s"]}), flush=True)
    return res


if __name__ == "__main__":
    main()
