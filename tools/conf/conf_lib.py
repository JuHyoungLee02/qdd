"""E-CONF pure helpers (docs/stage3/prereg_conf.md). numpy only (no torch) so the verdict runs anywhere.

A snapshot record (conf_extract.py): {id, ep, t, mse, disp, q: {question: {lp: {option: log-prob}, target: [..],
pred}}}. Confidence = min over questions of the top-1 minus top-2 option log-prob (E-NOV0 baseline); every score
below is a RISK (higher = more likely a large error):
  base        -min_q margin_q                                  (Part V, the registered definition)
  temp_min    -min_q margin_q / T_q                            per-question temperature (calibration split, NLL)
  temp_joint  -sum_q log p_cal,q(top-1)                         calibrated probability that every decision is right
  lr          logistic regression P(large error | clipped margins, min margin)       (calibration split)
  flow        log(flow-chunk dispersion over 1 + K noise draws)                       (extra expert passes)
  lr_flow     logistic regression on the lr features + log dispersion
  conf_set    sum_q (|split-conformal set_q| - 1), alpha 0.1, calibrated probabilities
Also: held-out episode selection, the episode-half split, joint (two-checkpoint) cluster bootstrap, the in-sample
90 % recall operating point and the runtime-use simulation (flag rate, Astra priority, conservative mode).
"""
from __future__ import annotations

import hashlib
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nov0"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import nov0_lib as N  # noqa: E402
from harvest.runtime.calibration import conformal_qhat, fit_temperature, pred_set  # noqa: E402

SCORES = ("base", "temp_min", "temp_joint", "lr", "flow", "lr_flow", "conf_set")
CLIP = 20.0
ALPHA = 0.1
L2 = 1.0
MSE_Q = 0.9
HALF_SALT = "conf_half@v1"
auroc = N.auroc
thr_for_recall = N.thr_for_recall
call_catch = N.call_catch


# ------------------------------------------------------------------------------------------ margins and errors
def margin(lp: dict) -> float:
    v = sorted((float(x) for x in lp.values()), reverse=True)
    return float(v[0] - v[1]) if len(v) > 1 else 99.0


def softmax(lp: dict) -> dict:
    m = max(float(x) for x in lp.values())
    e = {k: math.exp(float(x) - m) for k, x in lp.items()}
    s = sum(e.values())
    return {k: v / s for k, v in e.items()}


def snap_conf(qs: dict) -> dict:
    ms = {q: margin(d["lp"]) for q, d in qs.items()}
    a = min(ms, key=ms.get)
    return {"margins": ms, "min": ms[a], "argmin": a}


def q_correct(d: dict) -> bool:
    return d["pred"] in (d.get("target") or [])


def dec_error(rec: dict) -> bool:
    return not all(q_correct(d) for d in rec["q"].values())


def large_error(dec_err, mse, thr: float) -> np.ndarray:
    return np.asarray(dec_err, bool) | (np.asarray(mse, float) >= thr)


# ------------------------------------------------------------------------------------------ logistic regression
def logreg_fit(X, y, l2: float = L2, iters: int = 60) -> dict:
    """L2-penalised (weights only, standardised features) logistic regression by Newton steps."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 1e-12, sd, 1.0)
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]
    w = np.zeros(Z.shape[1])
    pen = np.r_[0.0, np.full(Z.shape[1] - 1, l2)]
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(Z @ w, -40, 40)))
        g = Z.T @ (p - y) + pen * w
        Hm = (Z * (p * (1 - p))[:, None]).T @ Z + np.diag(pen) + 1e-9 * np.eye(len(w))
        step = np.linalg.solve(Hm, g)
        w -= step
        if np.abs(step).max() < 1e-10:
            break
    return {"b": float(w[0]), "w": w[1:].tolist(), "mu": mu.tolist(), "sd": sd.tolist()}


def logreg_prob(m: dict, X) -> np.ndarray:
    X = np.atleast_2d(np.asarray(X, float))
    z = m["b"] + ((X - np.asarray(m["mu"])) / np.asarray(m["sd"])) @ np.asarray(m["w"])
    return 1 / (1 + np.exp(-np.clip(z, -40, 40)))


# ------------------------------------------------------------------------------------------ fits and scores
def features(rec: dict, f: dict) -> list:
    ms = snap_conf(rec["q"])["margins"]
    x = [min(ms.get(q, CLIP), CLIP) for q in f["qs"]]
    return x + [min(min(ms.values()), CLIP)]


def _log_disp(rec) -> float:
    return math.log(float(rec["disp"]) + 1e-12)


def _cal_probs(d: dict, T: float) -> dict:
    return softmax({k: float(v) / T for k, v in d["lp"].items()})


def risk(rec: dict, name: str, f: dict) -> float:
    qs = rec["q"]
    if name == "base":
        return -snap_conf(qs)["min"]
    if name == "temp_min":
        return -min(margin(d["lp"]) / f["temps"].get(q, 1.0) for q, d in qs.items())
    if name == "temp_joint":
        return float(sum(-math.log(max(max(_cal_probs(d, f["temps"].get(q, 1.0)).values()), 1e-300))
                         for q, d in qs.items()))
    if name == "lr":
        return float(logreg_prob(f["lr"], [features(rec, f)])[0])
    if name == "flow":
        return _log_disp(rec)
    if name == "lr_flow":
        return float(logreg_prob(f["lr_flow"], [features(rec, f) + [_log_disp(rec)]])[0])
    if name == "conf_set":
        return float(sum(len(pred_set(_cal_probs(d, f["temps"].get(q, 1.0)), f["qhat"].get(q, float("inf")))) - 1
                         for q, d in qs.items()))
    raise ValueError(f"score {name!r}")


def scores(recs, f: dict) -> dict:
    return {s: np.array([risk(r, s, f) for r in recs], float) for s in SCORES}


def labels(recs, mse_thr: float) -> np.ndarray:
    return large_error([dec_error(r) for r in recs], [r["mse"] for r in recs], mse_thr)


def fit(cal) -> dict:
    """Every calibration-split fit: questions, chunk-MSE q90 threshold (large-error target), per-question temperature
    (NLL of the target set), conformal q_hat (alpha 0.1, nonconformity 1 - p_cal of the best target option), the two
    logistic regressions, the Platt map of the base risk and each score's 90 % recall threshold."""
    qs = sorted({q for r in cal for q in r["q"]})
    f = {"qs": qs, "mse_thr": float(np.quantile([r["mse"] for r in cal], MSE_Q))}
    temps, qhat = {}, {}
    for q in qs:
        items = [{"probs": softmax(r["q"][q]["lp"]), "truth": r["q"][q]["target"]}
                 for r in cal if q in r["q"] and r["q"][q].get("target")]
        temps[q] = fit_temperature(items) if items else 1.0
        sc = [1 - max(_cal_probs(r["q"][q], temps[q]).get(k, 0.0) for k in r["q"][q]["target"])
              for r in cal if q in r["q"] and r["q"][q].get("target")]
        qhat[q] = conformal_qhat(sc, ALPHA)
    f.update(temps=temps, qhat=qhat)
    y = labels(cal, f["mse_thr"])
    X = np.array([features(r, f) for r in cal])
    f["lr"] = logreg_fit(X, y)
    f["lr_flow"] = logreg_fit(np.c_[X, [_log_disp(r) for r in cal]], y)
    base = np.array([risk(r, "base", f) for r in cal])
    f["platt"] = logreg_fit(base[:, None], y)
    s = scores(cal, f)
    f["tau90"] = {k: thr_for_recall(v, y, 0.9) for k, v in s.items()}
    return f


def platt_prob(f: dict, base_risk) -> float | np.ndarray:
    p = logreg_prob(f["platt"], np.asarray(base_risk, float).reshape(-1, 1))
    return float(p[0]) if np.ndim(base_risk) == 0 else p


# ------------------------------------------------------------------------------------------ held-out selection
def select_heldout(eps, cap: int, seed: int = 0) -> list:
    """Never-trained R2 episodes (valid False): (variant, task, kind, seed) tuples, at most `cap` per (variant, task)
    (seeded sample of the sorted list), sorted."""
    by = {}
    for e in sorted(eps, key=lambda e: (e["variant"], e["task"], e["kind"], e["seed"])):
        if not e["valid"]:
            by.setdefault((e["variant"], e["task"]), []).append((e["variant"], e["task"], e["kind"], int(e["seed"])))
    rng = random.Random(seed)
    out = []
    for key in sorted(by):
        xs = by[key]
        out += xs if len(xs) <= cap else rng.sample(xs, cap)
    return sorted(out)


def layout_unseen(item, eps) -> bool:
    """True when no variant of the same (task, kind, seed) layout was a training episode."""
    _, t, k, s = item
    return not any(e["valid"] and e["task"] == t and e["kind"] == k and int(e["seed"]) == s for e in eps)


# ------------------------------------------------------------------------------------------ splits and bootstrap
def half_of(ep: str, salt: str = HALF_SALT) -> int:
    return int(hashlib.sha256(f"{salt}|{ep}".encode()).hexdigest()[:8], 16) % 2


def joint_auroc(score_units: dict, y_units) -> dict:
    return {k: float(np.mean([auroc(s, y) for s, y in zip(v, y_units)])) for k, v in score_units.items()}


def _cluster_index(clusters):
    c = np.asarray(clusters)
    keys, inv = np.unique(c, return_inverse=True)
    return [np.flatnonzero(inv == j) for j in range(len(keys))]


def joint_draws(stat, score_units: dict, y_units, clusters, n_boot: int, seed: int = 0) -> dict:
    """Cluster bootstrap (episodes; every unit = one checkpoint on the SAME ordered snapshots, drawn together):
    {score: array of the per-draw mean over units of stat(score[ii], y[ii])}. Draws missing a class are skipped."""
    idx = _cluster_index(clusters)
    rng = np.random.default_rng(seed)
    out = {k: [] for k in score_units}
    for _ in range(n_boot):
        ii = np.concatenate([idx[j] for j in rng.integers(0, len(idx), len(idx))])
        ys = [np.asarray(y, bool)[ii] for y in y_units]
        if any(y.all() or not y.any() for y in ys):
            continue
        for k, v in score_units.items():
            out[k].append(np.mean([stat(np.asarray(s, float)[ii], y) for s, y in zip(v, ys)]))
    return {k: np.asarray(v) for k, v in out.items()}


def joint_auroc_draws(score_units, y_units, clusters, n_boot, seed=0):
    return joint_draws(auroc, score_units, y_units, clusters, n_boot, seed)


def reduction90(s, y) -> float:
    tau = thr_for_recall(s, y, 0.9)
    call, _ = call_catch(s, y, tau, strict=False)
    return 1.0 - call


# ------------------------------------------------------------------------------------------ flow dispersion
def noise_seeds(nidx: int, k_extra: int) -> list:
    """Flow-noise generator seeds of one snapshot: the primary draw = nidx (E-NOV0 / E-SR0 numbering, seed 0), extra
    draw e = 1..k_extra -> 1_000_003 * e + nidx (the numbering of seed e)."""
    return [int(nidx)] + [1_000_003 * e + int(nidx) for e in range(1, k_extra + 1)]


def dispersion(Z, valid) -> float:
    """Z [S, H, A] chunks of one snapshot (normalized action space) from S noise draws: mean over valid steps and
    action dims of the across-draw variance (ddof 0)."""
    Z = np.asarray(Z, float)
    v = np.asarray(valid, bool)
    return float(Z.var(axis=0)[v].mean())


# ------------------------------------------------------------------------------------------ runtime use
def runtime_sim(eps: dict, lat_s: float) -> dict:
    """eps: {episode: [(t seconds, flagged)]} in time order. Decision rate from the median decision spacing;
    Astra serial flow (canon §84 supplement 2) = one request every lat_s from the episode start; an interval is
    'priority' if a flag falls in it (canon §95 (a): the next request carries the flag and is sent when the in-flight
    one ends); conservative mode (§95 (b)) runs from the flag until that prioritised request's answer = the end of
    the NEXT interval; union of those spans clipped to the episode end (last t + spacing)."""
    gaps = [b[0] - a[0] for v in eps.values() for a, b in zip(v, v[1:])]
    dt = float(np.median(gaps))
    n_dec = sum(len(v) for v in eps.values())
    n_flag = sum(f for v in eps.values() for _, f in v)
    pri, n_int, cons, total, bouts = 0, 0, 0.0, 0.0, []
    for v in eps.values():
        t0, end = v[0][0], v[-1][0] + dt
        total += end - t0
        j = 0
        while t0 + j * lat_s < end - 1e-9:
            a, b = t0 + j * lat_s, t0 + (j + 1) * lat_s
            n_int += 1
            pri += any(f and a - 1e-9 <= t < b - 1e-9 for t, f in v)
            j += 1
        cur = None
        for t, f in v:
            if not f:
                continue
            j = math.floor((t - t0) / lat_s + 1e-9)
            lo, hi = t, min(t0 + (j + 2) * lat_s, end)
            if cur and lo <= cur[1] + 1e-9:
                cur[1] = max(cur[1], hi)
            else:
                if cur:
                    bouts.append(cur[1] - cur[0])
                cur = [lo, hi]
        if cur:
            bouts.append(cur[1] - cur[0])
    cons = float(sum(bouts))
    rate = 60.0 / dt
    return {"decision_dt_s": dt, "decisions_per_min": rate, "flag_frac": n_flag / n_dec,
            "flag_rate_per_min": rate * n_flag / n_dec, "priority_frac": pri / n_int if n_int else float("nan"),
            "priority_per_min": (pri / n_int) * 60.0 / lat_s if n_int else float("nan"),
            "conservative_frac": cons / total if total else float("nan"),
            "bout_median_s": float(np.median(bouts)) if bouts else 0.0, "n_bouts": len(bouts)}
