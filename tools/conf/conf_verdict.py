"""E-CONF verdict (docs/stage3/prereg_conf.md §5). Fixed at registration; not edited after results.

Inputs (conf_extract.py) in --dir: r2_c0_cal, r2_c0_test, r2_c1_cal, r2_c1_test, se2e_s1, se2e_s2 (.jsonl), plus the
held-out info json (layout-unseen episodes). Risk scores = conf_lib.SCORES (base = -min over questions of the top-1
minus top-2 option log-prob). Datasets, each = the mean over its two checkpoints on the same snapshots (joint):
  r2    fit on the calibration split (E-NOV0 eval split, 7,308) of the same checkpoint (C0 = E-MA2 c0, C1 = E-SR1c c1),
        evaluated on the never-trained held-out episodes (test)
  se2e  S-E2E val (motion_s1, motion_s2): two episode halves (conf_lib.half_of), every fit on the other half
        (out-of-fold), pooled
Large error = any decision wrong OR chunk MSE >= the fit split's chunk-MSE q90. Episode-cluster bootstrap 10,000
(draws shared by the two checkpoints and by every score).
Rules (CMP_EPS boundaries):
  Part V per dataset, per score: joint AUROC >= 0.75, joint in-sample call reduction at 90 % recall >= 0.30,
         fixed-threshold transfer recall (fit-split 90 % recall threshold applied to the evaluated snapshots)
         >= 0.85, scoring latency p95 <= 5 ms
  Part I per candidate: on BOTH datasets joint AUROC - base >= +0.03 and the Holm step-down (6 candidates, one-sided
         'greater' on the paired bootstrap difference) rejects, and added latency p95 <= 5 ms
  verdict: the best Part I candidate (largest min-over-datasets delta), else base; ADOPT_<score> for the first of
           those that passes Part V on both datasets, else NONE
  python tools/conf/conf_verdict.py --dir D --heldout J --out JSON [--boot 10000 --expect r2_cal=7308,...]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import conf_lib as L  # noqa: E402
from harvest.analysis.stats import at_least, at_most, holm_ci  # noqa: E402
from harvest.runtime.calibration import ece_mass  # noqa: E402

TH = {"auroc": 0.75, "reduction90": 0.30, "transfer_recall": 0.85, "lat_p95_ms": 5.0,
      "imp_delta": 0.03, "imp_lat_p95_ms": 5.0}
N_BOOT = 10000
LAT_S = 9.3      # serial Astra flow latency (canon §86 supplement 2, CoupleParams.latency_init_s)

RATES = (0.3, 0.2, 0.1)
DATASETS = ("r2", "se2e")
CANDS = tuple(s for s in L.SCORES if s != "base")
FLOW = ("flow", "lr_flow")


# ------------------------------------------------------------------------------------------ rules
def part_v(m: dict) -> bool:
    return bool(at_least(m["auroc"], TH["auroc"]) and at_least(m["reduction90"], TH["reduction90"])
                and at_least(m["transfer_recall"], TH["transfer_recall"]) and at_most(m["lat_p95_ms"], TH["lat_p95_ms"]))


def part_i(d: dict, lat_ms: float) -> bool:
    return bool(at_least(d["delta"], TH["imp_delta"]) and d["holm_reject"] and at_most(lat_ms, TH["imp_lat_p95_ms"]))


def decide(pv: dict, imp: dict, lat_added: dict) -> dict:
    passing = [s for s in imp if all(part_i(imp[s][d], lat_added[s]) for d in DATASETS)]
    best = None
    if passing:
        best = max(passing, key=lambda s: (min(imp[s][d]["delta"] for d in DATASETS), -L.SCORES.index(s)))
    order = ([best] if best else []) + ["base"]
    pass_v = {s: {d: part_v(pv[d][s]) for d in DATASETS} for s in order}
    verdict = next((f"ADOPT_{s}" for s in order if all(pass_v[s].values())), "NONE")
    return {"verdict": verdict, "improvement": best, "part_i_pass": passing, "pass_v": pass_v, "thresholds": TH}


# ------------------------------------------------------------------------------------------ units
def _unit(test, f_per, cal_base_per):
    """test records + a fit per record (list) + the calibration base scores per record (for rate thresholds)."""
    S = {s: np.array([L.risk(r, s, f) for r, f in zip(test, f_per)], float) for s in L.SCORES}
    y = np.array([L.labels([r], f["mse_thr"])[0] for r, f in zip(test, f_per)], bool)
    tau = {s: np.array([f["tau90"][s] for f in f_per]) for s in L.SCORES}
    for rate in RATES:
        tau[f"rate{rate}"] = np.array([np.quantile(c, 1 - rate) for c in cal_base_per])
    return {"recs": test, "fits": f_per, "S": S, "y": y, "tau": tau}


def unit_r2(cal, test):
    f = L.fit(cal)
    cb = np.array([L.risk(r, "base", f) for r in cal])
    u = _unit(test, [f] * len(test), [cb] * len(test))
    u["cal_auroc_base"] = L.auroc(cb, L.labels(cal, f["mse_thr"]))
    return u


def oof(recs) -> dict:
    h = np.array([L.half_of(r["ep"]) for r in recs])
    fits, cbs = {}, {}
    for a in (0, 1):
        other = [r for r, x in zip(recs, h) if x != a]
        fits[a] = L.fit(other)
        cbs[a] = np.array([L.risk(r, "base", fits[a]) for r in other])
    u = _unit(recs, [fits[x] for x in h], [cbs[x] for x in h])
    return {"scores": u["S"], "y": u["y"], "unit": u, "half": h}


# ------------------------------------------------------------------------------------------ dataset block
def _ci(draws, level=0.95):
    a = (1 - level) / 2
    return [float(np.quantile(draws, a)), float(np.quantile(draws, 1 - a))]


def _sub_auroc(units, mask_fn):
    vals = []
    for u in units:
        m = np.array([mask_fn(r) for r in u["recs"]], bool)
        a = L.auroc(u["S"]["base"][m], u["y"][m]) if m.any() else None
        if a is not None:
            vals.append(a)
    return {"auroc": float(np.mean(vals)) if vals else None, "n": int(sum(mask_fn(r) for r in units[0]["recs"]))}


def _per_question(units):
    qs = sorted({q for u in units for r in u["recs"] for q in r["q"]})
    out = {q: {"argmin_all": [], "argmin_large": [], "argmin_flag": [], "auroc_single": [], "auroc_loo": []}
           for q in qs}
    for u in units:
        M = np.array([[L.snap_conf(r["q"])["margins"].get(q, 99.0) for q in qs] for r in u["recs"]])
        am = M.argmin(1)
        flag = u["S"]["base"] >= u["tau"]["base"]
        for j, q in enumerate(qs):
            out[q]["argmin_all"].append(float((am == j).mean()))
            out[q]["argmin_large"].append(float((am[u["y"]] == j).mean()))
            out[q]["argmin_flag"].append(float((am[flag] == j).mean()) if flag.any() else float("nan"))
            out[q]["auroc_single"].append(L.auroc(-M[:, j], u["y"]))
            rest = np.delete(M, j, axis=1)
            out[q]["auroc_loo"].append(L.auroc(-rest.min(1), u["y"]) if rest.shape[1] else None)
    return {q: {k: (float(np.mean(v)) if all(x is not None for x in v) else None) for k, v in d.items()}
            for q, d in out.items()}


def _ece(units):
    raw, cal, per_q = [], [], {}
    lr = {"platt_base": [], "lr": [], "lr_flow": []}
    for u in units:
        pr, pc, cc, qq = [], [], [], []
        for r, f in zip(u["recs"], u["fits"]):
            for q, d in r["q"].items():
                pr.append(max(L.softmax(d["lp"]).values()))
                pc.append(max(L._cal_probs(d, f["temps"].get(q, 1.0)).values()))
                cc.append(L.q_correct(d))
                qq.append(q)
        pr, pc, cc, qq = map(np.asarray, (pr, pc, cc, qq))
        raw.append(ece_mass(pr, cc))
        cal.append(ece_mass(pc, cc))
        for q in sorted(set(qq)):
            m = qq == q
            per_q.setdefault(q, {"raw": [], "cal": []})
            per_q[q]["raw"].append(ece_mass(pr[m], cc[m]))
            per_q[q]["cal"].append(ece_mass(pc[m], cc[m]))
        pb = np.array([L.platt_prob(f, s) for f, s in zip(u["fits"], u["S"]["base"])])
        lr["platt_base"].append(ece_mass(pb, u["y"]))
        lr["lr"].append(ece_mass(u["S"]["lr"], u["y"]))
        lr["lr_flow"].append(ece_mass(u["S"]["lr_flow"], u["y"]))
    mean = lambda v: float(np.mean(v))  # noqa: E731
    return {"decision_raw": mean(raw), "decision_temp": mean(cal),
            "per_question": {q: {k: mean(v) for k, v in d.items()} for q, d in per_q.items()},
            "large_error_prob": {k: mean(v) for k, v in lr.items()}}


def _runtime(units, key_score, key_tau):
    res = []
    for u in units:
        eps = {}
        flag = u["S"][key_score] >= u["tau"][key_tau]
        for r, fl in zip(u["recs"], flag):
            eps.setdefault(r["ep"], []).append((float(r["t"]), bool(fl)))
        eps = {k: sorted(v) for k, v in eps.items()}
        x = L.runtime_sim(eps, LAT_S)
        x["recall"] = float(flag[u["y"]].mean())
        res.append(x)
    return {k: float(np.mean([x[k] for x in res])) for k in res[0]}


def cpu_latency(units, n=2000) -> dict:
    """p95 ms of computing each score from one record (python, the fitted objects already built)."""
    recs, f = units[0]["recs"][:n], units[0]["fits"][0]
    out = {}
    for s in L.SCORES:
        ts = []
        for r in recs:
            t0 = time.perf_counter()
            L.risk(r, s, f)
            ts.append(time.perf_counter() - t0)
        out[s] = float(np.quantile(ts, 0.95) * 1e3)
    return out


def block(units, n_boot: int, lat_flow_ms: float, seed: int = 0) -> dict:
    ids = [r["id"] for r in units[0]["recs"]]
    for u in units[1:]:
        if [r["id"] for r in u["recs"]] != ids:
            raise SystemExit("units are not on the same ordered snapshots")
    ys = [u["y"] for u in units]
    su = {s: [u["S"][s] for u in units] for s in L.SCORES}
    clusters = [r["ep"] for r in units[0]["recs"]]
    pts = L.joint_auroc(su, ys)
    draws = L.joint_auroc_draws(su, ys, clusters, n_boot, seed)
    au = {s: {"point": pts[s], "ci": _ci(draws[s]), "per_unit": [L.auroc(x, y) for x, y in zip(su[s], ys)]}
          for s in L.SCORES}
    holm = holm_ci(lambda k, lv: _ci(draws[k] - draws["base"], lv), list(CANDS), direction="greater")
    imp = {s: {"delta": pts[s] - pts["base"], "ci95": _ci(draws[s] - draws["base"]),
               "holm_reject": holm[s]["reject"], "holm_lo": holm[s]["lo"], "holm_level": holm[s]["level"]}
           for s in CANDS}
    red = {s: float(np.mean([L.reduction90(x, y) for x, y in zip(su[s], ys)])) for s in L.SCORES}
    red_draws = L.joint_draws(L.reduction90, {"base": su["base"]}, ys, clusters, n_boot, seed)["base"]
    tr = {}
    for s in L.SCORES:
        vals = []
        for u in units:
            fl = u["S"][s] >= u["tau"][s]
            vals.append((float(fl[u["y"]].mean()), float(fl.mean())))
        tr[s] = {"recall": float(np.mean([v[0] for v in vals])), "call": float(np.mean([v[1] for v in vals])),
                 "reduction": 1.0 - float(np.mean([v[1] for v in vals]))}
    lat = cpu_latency(units)
    lat_total = {s: lat[s] + (lat_flow_ms if s in FLOW else 0.0) for s in L.SCORES}
    pv = {s: {"auroc": pts[s], "reduction90": red[s], "transfer_recall": tr[s]["recall"], "lat_p95_ms": lat_total[s]}
          for s in L.SCORES}
    y_all = [u["y"] for u in units]
    out = {"n": len(ids), "n_ep": len(set(clusters)), "rate_large": float(np.mean([y.mean() for y in y_all])),
           "rate_dec": float(np.mean([np.mean([L.dec_error(r) for r in u["recs"]]) for u in units])),
           "rate_by_question": {q: float(np.mean([np.mean([not L.q_correct(r["q"][q]) for r in u["recs"] if q in r["q"]])
                                                  for u in units]))
                                for q in sorted({q for r in units[0]["recs"] for q in r["q"]})},
           "auroc": au, "improve": imp, "reduction90": {"point": red, "base_ci": _ci(red_draws)},
           "transfer": tr, "latency_cpu_p95_ms": lat, "latency_total_p95_ms": lat_total, "part_v": pv,
           "per_question": _per_question(units), "ece": _ece(units),
           "runtime": {"tau90": {s: _runtime(units, s, s) for s in L.SCORES},
                       "base_rates": {str(r): _runtime(units, "base", f"rate{r}") for r in RATES}}}
    # sensitivity (outside the verdict)
    q90 = []
    for u in units:
        mse = np.array([r["mse"] for r in u["recs"]])
        yy = L.large_error([L.dec_error(r) for r in u["recs"]], mse, float(np.quantile(mse, 0.9)))
        q90.append(L.auroc(u["S"]["base"], yy))
    out["sens_within_q90"] = float(np.mean(q90))
    groups = {}
    for key in ("variant", "task", "kind"):
        for g in sorted({r.get(key) for r in units[0]["recs"] if r.get(key) is not None}):
            groups[f"{key}={g}"] = _sub_auroc(units, lambda r, key=key, g=g: r.get(key) == g)
    out["sens_groups"] = groups
    if "cal_auroc_base" in units[0]:
        out["cal_auroc_base"] = [u["cal_auroc_base"] for u in units]
    return out


def compute(data: dict, n_boot: int = N_BOOT, lat_ms: dict | None = None, unseen=None, seed: int = 0) -> dict:
    lat_ms = lat_ms or {"r2": 0.0, "se2e": 0.0}
    r2u = [unit_r2(*data["r2"][k]) for k in sorted(data["r2"])]
    seu = [oof(data["se2e"][k])["unit"] for k in sorted(data["se2e"])]
    res = {"r2": block(r2u, n_boot, lat_ms["r2"], seed), "se2e": block(seu, n_boot, lat_ms["se2e"], seed)}
    if unseen is not None:
        keep = {tuple(x) for x in unseen}
        res["r2"]["sens_layout_unseen"] = _sub_auroc(
            r2u, lambda r: (r.get("variant"), r.get("task"), r.get("kind"), r.get("seed")) in keep)
    pv = {d: res[d]["part_v"] for d in DATASETS}
    imp = {s: {d: res[d]["improve"][s] for d in DATASETS} for s in CANDS}
    lat_added = {s: max(res[d]["latency_total_p95_ms"][s] for d in DATASETS) for s in CANDS}
    res["rules"] = decide(pv, imp, lat_added)
    res["lat_added"] = lat_added
    return res


# ------------------------------------------------------------------------------------------ files
FILES = {"r2": {"c0": ("r2_c0_cal", "r2_c0_test"), "c1": ("r2_c1_cal", "r2_c1_test")},
         "se2e": {"s1": "se2e_s1", "s2": "se2e_s2"}}


def read(path):
    recs, summ = [], None
    for x in open(path, encoding="utf-8"):
        d = json.loads(x)
        if d.get("event") == "summary":
            summ = d
        else:
            recs.append(d)
    ids = [r["id"] for r in recs]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{path}: duplicate ids")
    for r in recs:
        if not (np.isfinite(r["mse"]) and np.isfinite(r["disp"]) and r["q"]):
            raise SystemExit(f"{path}: {r['id']} non-finite mse / disp or no question")
    if summ is None:
        raise SystemExit(f"{path}: no summary line (incomplete run)")
    return recs, summ


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--heldout", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boot", type=int, default=N_BOOT)
    ap.add_argument("--expect", default="", help="name=n,... expected snapshot counts")
    a = ap.parse_args(argv)
    exp = dict(x.split("=") for x in a.expect.split(",") if x)
    data, summ = {"r2": {}, "se2e": {}}, {}
    for d, units in FILES.items():
        for k, names in units.items():
            loaded = []
            for nm in (names if isinstance(names, tuple) else (names,)):
                recs, s = read(os.path.join(a.dir, f"{nm}.jsonl"))
                if nm in exp and len(recs) != int(exp[nm]):
                    raise SystemExit(f"{nm}: {len(recs)} snapshots, expected {exp[nm]}")
                summ[nm] = s
                loaded.append(recs)
            data[d][k] = tuple(loaded) if len(loaded) > 1 else loaded[0]
    lat_ms = {"r2": max(summ[n]["latency_ms"]["added_p95"] for n in ("r2_c0_cal", "r2_c1_cal")),
              "se2e": max(summ[n]["latency_ms"]["added_p95"] for n in ("se2e_s1", "se2e_s2"))}
    unseen = json.load(open(a.heldout))["layout_unseen"]
    res = compute(data, a.boot, lat_ms, unseen)
    res["extract_latency_ms"] = {n: s.get("latency_ms") for n, s in summ.items()}
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps({"verdict": res["rules"]["verdict"]}))


if __name__ == "__main__":
    main()
