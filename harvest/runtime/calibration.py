"""Decision-probability calibration consumed by the runtime (canon §31 J5, §52; E §3.5-§3.7).

Per question: one temperature T (fit set half 1, NLL; E §3.6: logits = log p clipped at 1e-6) and split-conformal
thresholds q_hat per alpha (half 2; nonconformity = 1 - calibrated probability of the correct option, canon §31
bracket assumption). Prediction set = {options with 1 - p_cal <= q_hat}. The file is bound to the model fingerprint
and the question_id hashes (canon §28 E1: calibration is tied to question_id@vN x model; a mismatch refuses to load,
so the gate stays off). Written by `python -m harvest.eval.calib`, loaded by OursRuntime (RuntimeConfig.calibration).
"""
from __future__ import annotations

import json
import math

import numpy as np

FORMAT = "r6-calib-v1"
NE = "NONE_ESCALATE"
P_MIN = 1e-6


def apply_temperature(probs: dict, T: float) -> dict:
    if T == 1.0:
        return dict(probs)
    lg = {k: math.log(max(p, P_MIN)) / T for k, p in probs.items()}
    m = max(lg.values())
    e = {k: math.exp(v - m) for k, v in lg.items()}
    s = sum(e.values())
    return {k: v / s for k, v in e.items()}


def _p_true(probs: dict, truth) -> float:
    return max((probs.get(k, 0.0) for k in truth), default=0.0)


def nll(items, T: float) -> float:
    return float(np.mean([-math.log(max(_p_true(apply_temperature(x["probs"], T), x["truth"]), P_MIN))
                          for x in items]))


def fit_temperature(items) -> float:
    """argmin_T NLL on a log grid 0.05..20, then golden-section refinement."""
    grid = np.exp(np.linspace(math.log(0.05), math.log(20.0), 61))
    vals = [nll(items, float(t)) for t in grid]
    i = int(np.argmin(vals))
    lo, hi = math.log(grid[max(i - 1, 0)]), math.log(grid[min(i + 1, len(grid) - 1)])
    g = (math.sqrt(5) - 1) / 2
    a, b = hi - g * (hi - lo), lo + g * (hi - lo)
    for _ in range(40):
        if nll(items, math.exp(a)) < nll(items, math.exp(b)):
            hi = b
        else:
            lo = a
        a, b = hi - g * (hi - lo), lo + g * (hi - lo)
    return float(math.exp((lo + hi) / 2))


def conformal_qhat(scores, alpha: float) -> float:
    """Split-conformal threshold: the ceil((n+1)(1-alpha))-th smallest score; inf when that exceeds n."""
    s = sorted(float(x) for x in scores)
    n = len(s)
    r = math.ceil((n + 1) * (1 - alpha))
    return float("inf") if r > n or n == 0 else s[r - 1]


def pred_set(probs_cal: dict, qhat: float) -> set:
    return {k for k, p in probs_cal.items() if 1 - p <= qhat + 1e-12}


def ece_mass(p, correct, bins: int = 15) -> float:
    """ECE with equal-mass bins (E §3.4 "15개 동일 질량 구간")."""
    p, c = np.asarray(p, float), np.asarray(correct, float)
    if len(p) == 0:
        return float("nan")
    order = np.argsort(p, kind="stable")
    out = 0.0
    for idx in np.array_split(order, min(bins, len(p))):
        if len(idx):
            out += len(idx) / len(p) * abs(c[idx].mean() - p[idx].mean())
    return float(out)


def fit_question(fit_t, fit_c, alphas=(0.05, 0.1, 0.2)) -> dict:
    """fit_t: items for the temperature, fit_c: items for the conformal thresholds (disjoint episodes)."""
    from ..analysis.stats import ece
    T = fit_temperature(fit_t)
    raw_ece = ece([max(x["probs"].values()) for x in fit_t], [x["key"] in x["truth"] for x in fit_t])
    use_raw = raw_ece <= 0.03 and 0.8 <= T <= 1.25  # E §3.6
    Tu = 1.0 if use_raw else T
    scores = [1 - _p_true(apply_temperature(x["probs"], Tu), x["truth"]) for x in fit_c]
    return {"T": round(T, 6), "use_raw": bool(use_raw), "T_used": round(Tu, 6), "fit_raw_ece": round(raw_ece, 5),
            "n_fit_T": len(fit_t), "n_fit_j5": len(fit_c),
            "j5": {str(a): {"alpha": a, "qhat": conformal_qhat(scores, a)} for a in alphas}}


def _boot(by_cluster, stat, n, seed=0):
    from ..analysis.stats import cluster_bootstrap_ci
    if not by_cluster:
        return [None, None]
    lo, hi = cluster_bootstrap_ci(by_cluster, stat, n=n, seed=seed)
    return [round(lo, 4), round(hi, 4)]


def evaluate(items, qc: dict, alphas=(0.05, 0.1, 0.2), thetas=(0.6, 0.7, 0.8), n_boot: int = 2000) -> dict:
    """Held-out metrics of one question under its calibration qc (E §3.5 + J5 set metrics)."""
    from collections import defaultdict

    from ..analysis.stats import auroc, cluster_mean_ci, ece
    T = qc["T_used"]
    rows = []
    for x in items:
        pc = apply_temperature(x["probs"], T)
        k = max(pc, key=pc.get)
        rows.append({"c": x["cluster"], "ok": int(k in x["truth"]), "p_raw": x["probs"].get(k, 0.0), "p": pc[k],
                     "pc": pc, "truth": x["truth"]})
    byc = defaultdict(list)
    for r in rows:
        byc[r["c"]].append(r)

    def mci(vals_by_c):
        v = [z for vs in vals_by_c.values() for z in vs]
        if not v:
            return {"mean": None, "ci": [None, None], "n": 0}
        lo, hi = cluster_mean_ci(vals_by_c, n=n_boot)
        return {"mean": round(float(np.mean(v)), 4), "ci": [round(lo, 4), round(hi, 4)], "n": len(v)}
    p, ok = [r["p"] for r in rows], [r["ok"] for r in rows]
    ev = {"n": len(rows), "wrong": int(len(rows) - sum(ok)), "acc": mci({c: [r["ok"] for r in v] for c, v in byc.items()}),
          "ece_raw": round(ece([r["p_raw"] for r in rows], ok), 5), "ece_cal": round(ece(p, ok), 5),
          "ece_cal_mass": round(ece_mass(p, ok), 5),
          "ece_cal_ci": _boot({c: [(r["p"], r["ok"]) for r in v] for c, v in byc.items()},
                              lambda xs: ece([a for a, _ in xs], [b for _, b in xs]), n_boot),
          "brier_cal": round(float(np.mean([sum((pv - (k in r["truth"])) ** 2 for k, pv in r["pc"].items())
                                            for r in rows])), 5) if rows else None,
          "nll_cal": round(float(np.mean([-math.log(max(_p_true(r["pc"], r["truth"]), P_MIN)) for r in rows])), 5)
          if rows else None}
    a = auroc(p, ok)
    ev["auroc_raw"] = auroc([r["p_raw"] for r in rows], ok)

    def _au(xs):
        v = auroc([s for s, _ in xs], [y for _, y in xs])
        return 0.5 if v is None else v
    ev["auroc_cal"] = {"mean": None if a is None else round(a, 4),
                       "ci": _boot({c: [(r["p"], r["ok"]) for r in v] for c, v in byc.items()}, _au, n_boot)
                       if a is not None else [None, None]}
    ev["theta"] = {}
    for th in thetas:
        sel = {c: [r["ok"] for r in v if r["p"] >= th] for c, v in byc.items()}
        sel = {c: v for c, v in sel.items() if v}
        ev["theta"][str(th)] = {"acc": mci(sel), "coverage": round(float(np.mean([r["p"] >= th for r in rows])), 4)
                                if rows else None}
    ev["j5"] = {}
    for al in alphas:
        qh = qc["j5"][str(al)]["qhat"]
        sets = [(r, pred_set(r["pc"], qh)) for r in rows]
        cov = defaultdict(list)
        for r, s in sets:
            cov[r["c"]].append(int(bool(s & r["truth"])))
        sizes = [len(s) for _, s in sets]
        single = [(r, s) for r, s in sets if len(s) == 1]
        ev["j5"][str(al)] = {
            "qhat": qh, "coverage": mci(cov), "target": 1 - al,
            "set_size_mean": round(float(np.mean(sizes)), 4) if sizes else None,
            "set_size_dist": {str(k): sizes.count(k) for k in sorted(set(sizes))},
            "singleton_rate": round(len(single) / len(sets), 4) if sets else None,
            "empty_rate": round(float(np.mean([len(s) == 0 for _, s in sets])), 4) if sets else None,
            "hold_rate": round(float(np.mean([len(s) != 1 or NE in s for _, s in sets])), 4) if sets else None,
            "ne_in_set_rate": round(float(np.mean([NE in s for _, s in sets])), 4) if sets else None,
            "singleton_acc": round(float(np.mean([bool(s & r["truth"]) for r, s in single])), 4) if single else None}
    return ev


def judge_question(ev: dict, n_fit_j5: int, thetas=(0.6, 0.7, 0.8)) -> dict:
    """E §3.7 judgment 1 (theta gate per candidate theta) and judgment 8 (J5 per alpha); AUROC not judgeable with
    < 30 wrong items (gate stays off); J5 'no guarantee' with < 400 fit items (CoFineLLM size, [가정])."""
    judgeable = ev["wrong"] >= 30
    au = ev["auroc_cal"]
    ece_ok = ev["ece_cal"] <= 0.05 and ev["ece_cal_ci"][1] is not None and ev["ece_cal_ci"][1] <= 0.08
    au_ok = judgeable and au["mean"] is not None and au["mean"] >= 0.75 and (au["ci"][0] or 0) >= 0.70
    out = {"auroc_judgeable": judgeable, "ece_ok": bool(ece_ok), "auroc_ok": bool(au_ok), "theta_gate": {},
           "j5_ok": {}, "j5_guarantee": n_fit_j5 >= 400}
    for th in thetas:
        t = ev["theta"].get(str(th))
        if not t or t["acc"]["mean"] is None:
            out["theta_gate"][str(th)] = False
            continue
        out["theta_gate"][str(th)] = bool(ece_ok and au_ok and t["acc"]["mean"] >= th - 0.03
                                          and t["acc"]["ci"][0] >= th - 0.08 and t["coverage"] >= 0.20)
    for al, j in ev["j5"].items():
        a = float(al)
        out["j5_ok"][al] = bool(j["coverage"]["ci"][0] is not None and j["coverage"]["ci"][0] >= 1 - a - 0.03
                                and (j["singleton_rate"] or 0) >= 0.5 and j["singleton_acc"] is not None
                                and j["singleton_acc"] >= 1 - a)
    return out


class Calibration:
    """Loaded calibration file; apply() -> calibrated option probabilities, set_for() -> J5 prediction set."""

    def __init__(self, d: dict):
        self.d = d
        self.q = d["questions"]

    @classmethod
    def load(cls, path: str, fingerprint: str | None = None, question_ids: dict | None = None) -> "Calibration":
        d = json.load(open(path, encoding="utf-8"))
        if d.get("format") != FORMAT:
            raise ValueError(f"{path}: format {d.get('format')!r} != {FORMAT}")
        fp = (d.get("model") or {}).get("fingerprint")
        if fingerprint is not None and fp is not None and fp != fingerprint:
            raise ValueError(f"calibration model fingerprint {fp} != served model {fingerprint} (recalibrate)")
        if question_ids is not None:
            for q, qid in (d.get("question_ids") or {}).items():
                if q in question_ids and qid.split("@")[0] != question_ids[q].split("@")[0]:
                    raise ValueError(f"question_id of {q}: calibrated {qid} != runtime {question_ids[q]}")
        return cls(d)

    def apply(self, q: str, probs: dict) -> dict:
        c = self.q.get(q)
        return dict(probs) if c is None else apply_temperature(probs, c["T_used"])

    def j5_on(self, q: str, alpha: float) -> bool:
        c = self.q.get(q)
        return bool(c and (c.get("j5_ok") or {}).get(str(alpha)))

    def set_for(self, q: str, probs_cal: dict, alpha: float) -> set:
        return pred_set(probs_cal, self.q[q]["j5"][str(alpha)]["qhat"])
