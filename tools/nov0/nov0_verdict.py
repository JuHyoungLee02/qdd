"""E-NOV0 verdict (docs/stage3/prereg_nov0.md §5-§6). Fixed at registration; not edited after results.

Inputs (nov0_extract.py): <dir>/{mem,cal,eval,se2e}.npz (ids + features dec / mean / vis) and .meta.jsonl, the
latency json (nov0_latency.py). Novelty score = mean cosine distance to the k = 10 nearest reference rows after
centring with the reference mean and unit norm (cl2n); variant dec/raw = no centring.
  shift_dr    ref = memory standard, in = eval standard, shifted = eval dr        (class-stratified cluster bootstrap)
  shift_task  per task t: ref = memory without t, in = eval without t, shifted = eval t; mean over the 3 tasks
  shift_real  ref = memory, in = eval (R2 sim), shifted = S-E2E val (real robot) -- sanity gate G5
  err         ref = memory, scores of eval: AUROC for large error (any decision wrong OR chunk MSE >= eval q90),
              decision error, chunk error; fixed thresholds = calibration-score quantiles; 90 % recall operating point
              (in-sample) and the two-half cross-fit
Rules on the primary variant (dec/cl2n), CMP_EPS boundaries:
  R1 gate  err AUROC >= 0.75, call reduction at 90 % recall >= 0.30, cross-fit held-out recall >= 0.85,
           GPU scoring p95 <= 5 ms
  R2 nov   dr AUROC >= 0.80, mean task-holdout AUROC >= 0.80, eval flag rate at calibration q95 <= 0.07
  G5       real-vs-sim AUROC >= 0.90, else HOLD_G5 (pipeline check before any verdict)
  verdict  GATE+NOV (R1, R2) | GATE (R1) | NOV (R2) | NONE
  python tools/nov0/nov0_verdict.py --dir D --latency J --out JSON [--boot 10000 --boot2 2000 --expect-eval N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import nov0_lib as L  # noqa: E402
from harvest.analysis.stats import at_least, at_most  # noqa: E402

PRIMARY = "dec/cl2n"
VARIANTS = ("dec/cl2n", "mean/cl2n", "vis/cl2n", "dec/raw")
K = 10
FIXED_Q = (0.5, 0.7, 0.8, 0.9, 0.95)
SETS = ("mem", "cal", "eval", "se2e")
TH = {"err_auroc": 0.75, "reduction90": 0.30, "xfit_recall": 0.85, "lat_gpu_p95_ms": 5.0,
      "dr_auroc": 0.80, "task_auroc_mean": 0.80, "fa95": 0.07, "real_auroc": 0.90}


# ------------------------------------------------------------------------------------------ rules
def rules(m: dict) -> dict:
    r1 = (at_least(m["err_auroc"], TH["err_auroc"]) and at_least(m["reduction90"], TH["reduction90"])
          and at_least(m["xfit_recall"], TH["xfit_recall"]) and at_most(m["lat_gpu_p95_ms"], TH["lat_gpu_p95_ms"]))
    r2 = (at_least(m["dr_auroc"], TH["dr_auroc"]) and at_least(m["task_auroc_mean"], TH["task_auroc_mean"])
          and at_most(m["fa95"], TH["fa95"]))
    g5 = at_least(m["real_auroc"], TH["real_auroc"])
    v = "HOLD_G5" if not g5 else "GATE+NOV" if r1 and r2 else "GATE" if r1 else "NOV" if r2 else "NONE"
    return {"verdict": v, "r1": bool(r1), "r2": bool(r2), "g5": bool(g5), "inputs": m, "thresholds": TH}


# ------------------------------------------------------------------------------------------ inputs
def check_inputs(data: dict, expect: dict) -> None:
    for s in SETS:
        d = data[s]
        n = len(d["ids"])
        if len(set(d["ids"])) != n:
            raise SystemExit(f"{s}: duplicate ids")
        if [m["id"] for m in d["meta"]] != list(d["ids"]):
            raise SystemExit(f"{s}: meta ids differ from feature ids")
        for f, X in d["feat"].items():
            if X.shape[0] != n or not np.isfinite(X).all():
                raise SystemExit(f"{s}/{f}: shape {X.shape} for {n} ids or non-finite values")
        if s in expect and n != expect[s]:
            raise SystemExit(f"{s}: {n} ids, expected {expect[s]}")
    seeds = {s: {m["seed"] for m in data[s]["meta"]} for s in ("mem", "cal", "eval")}
    if seeds["mem"] & seeds["cal"] or (seeds["mem"] | seeds["cal"]) & seeds["eval"]:
        raise SystemExit("scene seeds overlap between memory / calibration / eval")
    for m in data["eval"]["meta"]:
        if not np.isfinite(m.get("mse", np.nan)):
            raise SystemExit(f"eval {m['id']}: no chunk MSE")


# ------------------------------------------------------------------------------------------ metrics
def _score(ref, query, mode):
    mu = ref.mean(0) if mode == "cl2n" else np.zeros(ref.shape[1])
    return L.knn_score(L.cl2n(query, mu), L.cl2n(ref, mu), K)


def _col(meta, key):
    return np.array([m[key] for m in meta])


def _spearman(a, b):
    """Spearman rho (ordinal ranks; the inputs are continuous)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def _shift(ref, xin, xout, ep_in, ep_out, mode, nb, seed, cal=None):
    s = _score(ref, np.vstack([xin, xout]), mode)
    y = np.r_[np.zeros(len(xin), bool), np.ones(len(xout), bool)]
    ep = np.r_[np.asarray(ep_in, str), np.asarray(ep_out, str)]
    out = {"auroc": L.auroc(s, y), "n_in": int(len(xin)), "n_out": int(len(xout))}
    if nb:
        out["ci"] = L.auroc_ci(s, y, ep, n=nb, seed=seed, stratify=True)
    if cal is not None:
        tau = float(np.quantile(_score(ref, cal, mode), 0.95))
        out.update(tau95=tau, flag_in=float((s[~y] > tau).mean()), flag_out=float((s[y] > tau).mean()))
    return out


def _err_block(s, s_cal, large, dec_err, chunk_big, mse, ep, nb, seed):
    out = {"auroc_large": L.auroc(s, large), "auroc_dec": L.auroc(s, dec_err), "auroc_chunk": L.auroc(s, chunk_big),
           "spearman_mse": _spearman(s, mse)}
    if nb:
        out["ci_large"] = L.auroc_ci(s, large, ep, n=nb, seed=seed)
    if s_cal is not None:
        rows = []
        for q in FIXED_Q:
            tau = float(np.quantile(s_cal, q))
            call, catch = L.call_catch(s, large, tau)
            _, catch_dec = L.call_catch(s, dec_err, tau)
            _, catch_chunk = L.call_catch(s, chunk_big, tau)
            rows.append({"q": q, "tau": tau, "call": call, "catch": catch, "catch_dec": catch_dec,
                         "catch_chunk": catch_chunk})
        out["fixed"] = rows
    tau = L.thr_for_recall(s, large, 0.9)
    call, rec = L.call_catch(s, large, tau, strict=False)
    out["op90"] = {"tau": tau, "call": call, "recall": rec, "reduction": 1.0 - call}
    out["xfit"] = L.crossfit(s, large, ep, 0.9)
    return out


def compute(data: dict, boot_primary: int = 10000, boot_secondary: int = 2000, seed: int = 0) -> dict:
    mem, cal, ev, se = (data[s]["meta"] for s in SETS)
    mv, mt = _col(mem, "variant"), _col(mem, "task")
    cv = _col(cal, "variant")
    ev_v, ev_t, ev_ep = _col(ev, "variant"), _col(ev, "task"), _col(ev, "ep").astype(str)
    se_ep = _col(se, "ep").astype(str)
    dec_err = np.array([not all(m["correct"].values()) for m in ev])
    mse = _col(ev, "mse").astype(float)
    large, thr = L.large_error(dec_err, mse, 0.9)
    chunk_big = mse >= thr
    out = {"n": {s: len(data[s]["ids"]) for s in SETS},
           "targets": {"n_large": int(large.sum()), "rate_large": float(large.mean()), "rate_dec": float(dec_err.mean()),
                       "mse_q90": thr, "rate_by_question": {q: float(np.mean([not m["correct"][q] for m in ev]))
                                                            for q in ev[0]["correct"]}},
           "features": {}}
    tasks = sorted(set(mt))
    for var in VARIANTS:
        fname, mode = var.split("/")
        nb = boot_primary if var == PRIMARY else boot_secondary
        F = {s: data[s]["feat"][fname] for s in SETS}
        std, dr = ev_v == "standard", ev_v == "dr"
        r = {"shift_dr": _shift(F["mem"][mv == "standard"], F["eval"][std], F["eval"][dr], ev_ep[std], ev_ep[dr],
                                mode, nb, seed, cal=F["cal"][cv == "standard"])}
        per = {}
        for t in tasks:
            a, b = ev_t != t, ev_t == t
            per[t] = _shift(F["mem"][mt != t], F["eval"][a], F["eval"][b], ev_ep[a], ev_ep[b], mode, nb, seed)
        r["shift_task"] = {"per_task": per, "mean": float(np.mean([per[t]["auroc"] for t in tasks]))}
        r["shift_real"] = _shift(F["mem"], F["eval"], F["se2e"], ev_ep, se_ep, mode, 0, seed)
        s = _score(F["mem"], F["eval"], mode)
        s_cal = _score(F["mem"], F["cal"], mode)
        r["err"] = _err_block(s, s_cal, large, dec_err, chunk_big, mse, ev_ep, nb, seed)
        r["err"]["fa95"] = next(x["call"] for x in r["err"]["fixed"] if x["q"] == 0.95)
        r["err"]["by_variant"] = {v: L.auroc(s[ev_v == v], large[ev_v == v]) for v in ("standard", "dr")}
        out["features"][var] = r
    margin = np.array([min(m["margin"].values()) for m in ev])
    out["baseline_margin"] = _err_block(-margin, None, large, dec_err, chunk_big, mse, ev_ep, boot_secondary, seed)
    return out


def primary_metrics(res: dict, lat: dict) -> dict:
    p = res["features"][PRIMARY]
    return {"err_auroc": p["err"]["auroc_large"], "reduction90": p["err"]["op90"]["reduction"],
            "xfit_recall": p["err"]["xfit"]["recall"], "lat_gpu_p95_ms": lat["gpu"]["p95_ms"],
            "dr_auroc": p["shift_dr"]["auroc"], "task_auroc_mean": p["shift_task"]["mean"],
            "fa95": p["err"]["fa95"], "real_auroc": p["shift_real"]["auroc"]}


# ------------------------------------------------------------------------------------------ files
def load_dir(d: str) -> dict:
    data = {}
    for s in SETS:
        z = np.load(os.path.join(d, f"{s}.npz"))
        meta = [json.loads(x) for x in open(os.path.join(d, f"{s}.meta.jsonl"), encoding="utf-8")]
        meta = [m for m in meta if m.get("event") != "summary"]
        data[s] = {"ids": [str(x) for x in z["ids"]], "meta": meta,
                   "feat": {f: z[f].astype(np.float64) for f in ("dec", "mean", "vis")}}
    return data


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--latency", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--boot2", type=int, default=2000)
    ap.add_argument("--expect-eval", type=int, default=0)
    a = ap.parse_args(argv)
    data = load_dir(a.dir)
    check_inputs(data, {"eval": a.expect_eval} if a.expect_eval else {})
    res = compute(data, a.boot, a.boot2, 0)
    lat = json.load(open(a.latency))
    res["latency"] = lat
    res["rules"] = rules(primary_metrics(res, lat))
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps({"verdict": res["rules"]["verdict"], "r1": res["rules"]["r1"], "r2": res["rules"]["r2"],
                      "g5": res["rules"]["g5"]}))


if __name__ == "__main__":
    main()
