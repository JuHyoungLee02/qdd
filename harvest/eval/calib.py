"""E1 calibration (E §3, canon §31 J5, §52) -- one command, writes the runtime calibration file (M4 gate).

  python -m harvest.eval.calib --model <merged | adapter | zero-shot> --out DIR \
      --fit-data DIR[,DIR] --fit-split cal --heldout DIR[,DIR] --heldout-split test|dev|pool \
      [--alphas 0.05,0.1,0.2] [--thetas 0.6,0.7,0.8] [--truth labels_v2|outcome:<rule>] [--decision-only]

The model is asked every snapshot once (A0, S1 1 mm, §59 lead). Fit episodes are split in two halves by episode
(§52: half 1 = per-question temperature, half 2 = J5 split-conformal thresholds); the held-out folders give the
reported ECE (equal-width and equal-mass, 15 bins) / AUROC / theta-gate accuracy and coverage / J5 coverage, set
sizes, singleton rate, NONE_ESCALATE-in-set rate, singleton accuracy, with episode-cluster CIs, and the E §3.7
judgments 1 and 8 per question. <out>/calibration.json is what OursRuntime loads (RuntimeConfig.calibration); it is
bound to the model fingerprint and the question_id hashes. CAL (500-549) / TEST (1000-1149) need --*-split cal|test
AND HARVEST_ALLOW_SPLIT (main session only, pre-registered time); smoke runs use dev / pool as stand-ins.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from types import SimpleNamespace

from ..runtime import calibration as K


def halves(clusters) -> tuple[set, set]:
    """Deterministic episode split: order by sha256 of the cluster id, alternate."""
    cs = sorted(set(clusters), key=lambda c: hashlib.sha256(repr(c).encode()).hexdigest())
    return set(cs[0::2]), set(cs[1::2])


def items_from(eps, done, truth, questions, decision_only=False) -> dict:
    """{question: [{cluster, probs (by option_key), truth (set), key}]} from the A0 calls."""
    out = {q: [] for q in questions}
    for ep in eps:
        for ln in ep["lines"]:
            if decision_only and not ln.get("decision"):
                continue
            r = done.get((ep["dir"], ep["seed"], ln["k"], "A0#0"))
            t = truth.get((ep["kind"], ep["seed"], ln["k"]))
            if r is None or t is None:
                continue
            for q in questions:
                a = r["answers"].get(q)
                if a is None or q not in t or not a.get("probs"):
                    continue
                out[q].append({"cluster": (ep["kind"], ep["seed"]), "probs": a["probs"], "truth": t[q],
                               "key": a["key"]})
    return out


def _args(argv):
    ap = argparse.ArgumentParser(prog="python -m harvest.eval.calib", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fit-data", required=True)
    ap.add_argument("--fit-split", required=True)
    ap.add_argument("--heldout", required=True)
    ap.add_argument("--heldout-split", required=True)
    ap.add_argument("--episodes", type=int, default=0)
    ap.add_argument("--alphas", default="0.05,0.1,0.2")
    ap.add_argument("--thetas", default="0.6,0.7,0.8")
    ap.add_argument("--truth", default="labels_v2")
    ap.add_argument("--outcome-dirs", default="")
    ap.add_argument("--decision-only", action="store_true")
    ap.add_argument("--layout", default="auto")
    ap.add_argument("--mode", default="lead")
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--gpu", default="3")
    ap.add_argument("--gpu-util", type=float, default=0.30)
    ap.add_argument("--url", default="")
    ap.add_argument("--served-name", default="")
    ap.add_argument("--n-boot", type=int, default=2000)
    return ap.parse_args(argv)


def _md(rep, meta) -> str:
    from .common import ci_str, md_table
    rows = []
    for q, r in rep["questions"].items():
        ev, j = r["heldout"], r["judgment"]
        if ev is None:
            rows.append([q, r["fit"]["T"], r["fit"]["use_raw"], 0] + ["-"] * 14)
            continue
        j5 = ev["j5"].get("0.1") or next(iter(ev["j5"].values()))
        rows.append([q, r["fit"]["T"], r["fit"]["use_raw"], ev["n"], ci_str(ev["acc"]), ev["ece_raw"], ev["ece_cal"],
                     ev["ece_cal_mass"], ev["auroc_cal"]["mean"], ci_str(j5["coverage"]), j5["set_size_mean"],
                     j5["singleton_rate"], j5["empty_rate"], j5["ne_in_set_rate"], j5["singleton_acc"],
                     ",".join(k for k, v in j["theta_gate"].items() if v) or "-",
                     ",".join(k for k, v in j["j5_ok"].items() if v) or "-", j["j5_guarantee"]])
    return "\n".join([
        f"# E1 calibration — {meta['model']['spec']}", "",
        f"- utc {meta['utc']}, git {meta['git']}, code_sha {meta['code_sha']}, model fingerprint "
        f"{meta['model'].get('fingerprint')}, prompt_config {meta['prompt_config']['sha']} (layout {meta['layout']}), "
        f"fit split {meta['fit_split']} ({meta['n_fit_episodes']} ep: T {meta['n_T_episodes']} / J5 "
        f"{meta['n_J5_episodes']}), held-out split {meta['heldout_split']} ({meta['n_heldout_episodes']} ep)",
        f"- runtime file: {meta['calibration_file']}", "",
        md_table(["question", "T", "raw", "n", "acc", "ECE raw", "ECE cal", "ECE cal (mass)", "AUROC", "J5 cov (a=.1)",
                  "set size", "singleton", "empty set", "NE in set", "singleton acc", "theta gate ok", "J5 ok (alpha)",
                  "J5 >=400 fit"], rows)])


def main(argv=None):
    from . import common as C
    from .e05 import _collect
    from .splits import check_split
    a = _args(argv)
    check_split(a.fit_split)
    check_split(a.heldout_split)
    t0 = time.monotonic()
    os.makedirs(a.out, exist_ok=True)
    os.environ.setdefault("HARVEST_QID_REGISTRY", os.path.join(a.out, "qid_registry.json"))
    info = C.ensure_merged(C.resolve_model(a.model), a.out)
    fit = C.load_episodes([d for d in a.fit_data.split(",") if d], a.fit_split, a.episodes)
    held = C.load_episodes([d for d in a.heldout.split(",") if d], a.heldout_split, a.episodes)
    fitc = {(e["dir"], e["seed"]) for e in fit}
    if any((e["dir"], e["seed"]) in fitc for e in held):
        raise SystemExit("fit and held-out share episodes")
    od = [d for d in a.outcome_dirs.split(",") if d]
    truth = {**C.load_truth(fit, a.truth, od), **C.load_truth(held, a.truth, od)}
    pc = C.training_prompt_config(info["path"]) if info["kind"] != "mock" else None
    layout = C.default_layout(pc) if a.layout == "auto" else a.layout
    alphas = tuple(float(x) for x in a.alphas.split(","))
    thetas = tuple(float(x) for x in a.thetas.split(","))
    ns = SimpleNamespace(same_k=1, variants="A0", blocks=0, floor_n=0, conc=a.conc)
    with C.Server(info, a.gpu, a.out, a.url, a.served_name, a.gpu_util) as srv:
        asker = C.MockAsker() if info["kind"] == "mock" else C.Asker(srv.url, srv.name, layout, a.mode)

        async def run():
            try:
                return await _collect(asker, fit + held, ns, a.out)
            finally:
                await asker.close()
        t1 = time.monotonic()
        done = asyncio.run(run())
        t_calls = time.monotonic() - t1
    I_fit = items_from(fit, done, truth, C.QUESTIONS, a.decision_only)
    I_held = items_from(held, done, truth, C.QUESTIONS, a.decision_only)
    hT, hC = halves([(e["kind"], e["seed"]) for e in fit])
    from ..runtime.run_r5 import question_ids
    qids = question_ids(layout)
    fp = C.model_fingerprint(info["path"]) if info.get("path") else "mock"
    rep, calq = {"questions": {}}, {}
    for q in C.QUESTIONS:
        ft = [x for x in I_fit[q] if x["cluster"] in hT]
        fc = [x for x in I_fit[q] if x["cluster"] in hC]
        if not ft or not fc:
            continue
        qc = K.fit_question(ft, fc, alphas)
        ev = K.evaluate(I_held[q], qc, alphas, thetas, a.n_boot) if I_held[q] else None
        jd = K.judge_question(ev, qc["n_fit_j5"], thetas) if ev else {"theta_gate": {}, "j5_ok": {}}
        calq[q] = {**qc, "j5_ok": jd["j5_ok"], "theta_gate": jd["theta_gate"]}
        rep["questions"][q] = {"fit": qc, "heldout": ev, "judgment": jd}
    cal = {"format": K.FORMAT, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "model": {"spec": info["spec"], "path": info.get("path"), "fingerprint": fp},
           "question_ids": qids, "layout": layout, "prompt_config_sha": C.prompt_config_eval(layout)["sha"],
           "fit_split": a.fit_split, "questions": calq,
           "note": "J5 gate is used only for (question, alpha) with j5_ok; theta gate not wired in the runtime (E1 §3.7:"
                   " a question uses J5 or theta, not both)"}
    cal_path = os.path.join(a.out, "calibration.json")
    json.dump(cal, open(cal_path, "w", encoding="utf-8"), indent=1)
    meta = C.run_meta("calib", info, {
        "fit_split": a.fit_split, "heldout_split": a.heldout_split, "fit_data": a.fit_data, "heldout": a.heldout,
        "seeds": {"fit": sorted({e["seed"] for e in fit}), "heldout": sorted({e["seed"] for e in held})},
        "n_fit_episodes": len(fit), "n_T_episodes": len(hT), "n_J5_episodes": len(hC), "n_heldout_episodes": len(held),
        "truth": a.truth, "layout": layout, "mode": a.mode, "prompt_config": C.prompt_config_eval(layout),
        "question_ids": qids, "calibration_file": cal_path, "decision_only": a.decision_only,
        "errors": sum(1 for r in done.values() if r.get("error")),
        "runtime_s": {"total": round(time.monotonic() - t0, 1), "calls": round(t_calls, 1),
                      "vllm_ready": round(getattr(srv, "t_ready", 0.0), 1)}})
    C.write_outputs(a.out, "calib", {"meta": meta, "result": rep}, _md(rep, meta))
    print("CALIB_DONE " + json.dumps({"out": a.out, "file": cal_path, "runtime_s": meta["runtime_s"]}), flush=True)
    return rep


if __name__ == "__main__":
    main()
