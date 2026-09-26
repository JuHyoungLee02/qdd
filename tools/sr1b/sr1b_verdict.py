"""E-SR1b verdict (docs/stage3/prereg_sr1b.md §5, fixed before the main runs; not edited after results).

  python tools/sr1b/sr1b_verdict.py --manifest JSON --latency JSON --n 1200 --out JSON

Two adherence metrics, each with the target 0.8, reported and decided SEPARATELY (main decides with the user which
one binds adoption):
  stress     A_xy = tools/sr0/sr0_verdict.py unchanged (load, snap_stats, pool, boot_ci): counterfactual directions
             (every one of the 8 except the label's), hit = cos(chunk xy, forced direction) > 0.5; chance = the same
             chunk against shuffled forced labels.
  plausible  P_xy (added here): reference r = the 8-sector of the RECORDED chunk displacement (disp_gt, |xy| >= 2 mm;
             else the snapshot has no pair); plausible edits d = r +- 45 deg (the neighbouring bins -- the finest
             rotation the 8-bin decision vocabulary can express); hit = the chunk under xy:d has |xy| >= 0.1 mm,
             cos(chunk, d) > 0.5 AND cos(chunk, d) > cos(chunk, r) (it moved past the bisector toward the edit);
             chance = the same chunk scored against both neighbours (mean). Reported with it: the shift
             delta = chunk(xy:d) - chunk(xy:r): rate of cos(delta, e_d) > 0.5 (e_d = unit(d) - unit(r), normalized)
             and the mean projection on e_d (mm); and the plain cos(chunk, d) > 0.5 rate (not discriminating: a chunk
             along r already has cos 0.71).
Strata (reported, outside the rule): free space / near contact / unknown by the record's `near` flag
(harvest.train.sr1b.near_snap = runtime.core.near_contact from the row's aux geometry, 5 cm).
Gripper timing (non-inferiority): grip_acc = the `pred` chunk's last-target gripper state (open = openness >= 0.5)
equals the recorded chunk's last state, all snapshots; reported with it the transition subset (recorded first and last
states differ) accuracy.
Distance CFG cells (derived, no extra GPU): for every (w_free, w_near) in DCFG, per snapshot the w_free record in free
space and the w_near record near contact or when the distance is unknown; label d<w_free>.
Seeds pooled (pairs summed), snapshot bootstrap paired over seeds (10,000, seed 0). Decision accuracy = every decision
item, prediction in the item's target set (E-MA2 no-command accuracy).
Manifest: {"baseline": [C0 seed files at w = 1], "arms": {name: {w: [seed files]}}} (w as text, e.g. "1.5").
Rule (CMP_EPS 1e-12), per metric m in (a_xy, p_xy) and cell (arm in RULE_ARMS, w or d<w>):
  pass_m = m >= 0.8  and  bootstrap 2.5 % of m > chance_m + 0.1
           and decision accuracy - baseline >= -0.01  and  MSE(pred) / baseline MSE(pred) - 1 <= 0.05
           and grip_acc - baseline >= -0.01
           and (no CFG  or  FULL p95 latency CFG / plain - 1 <= 0.10)
  ADOPT        the passing cell with the highest m (ties: smaller w, plain before distance CFG, then RULE_ARMS order)
  NOT_REACHED  no passing cell; best = the highest-m cell meeting the non-inferiority conditions (else the highest m
               overall, flagged)
Arms outside RULE_ARMS (the single-seed dropout 0.2 arm) are reported, never adopted.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))

import sr0_eval as E0  # noqa: E402
import sr0_verdict as V0  # noqa: E402
from harvest.train.sr1b import XY_MIN_M, sector_xy, w_tag  # noqa: E402

EPS = 1e-12
A_MIN, LB_MARGIN, DEC_MIN, MSE_MAX, LAT_MAX, GRIP_MIN = 0.8, 0.1, -0.01, 0.05, 0.10, -0.01
RULE_ARMS = ("A", "B", "AB")
DCFG = ((3.0, 1.0), (5.0, 1.0))
METRICS = {"a_xy": ("lb", "chance_xy"), "p_xy": ("p_lb", "p_chance")}
P_KEYS = ("p_pairs", "p_hits", "p_chance", "p_shift_hits", "p_shift_mm", "p_abs")
GRIP_OPEN = 0.5


def dec_counts(snaps) -> tuple:
    """(correct, total) over every decision item: prediction in the item's target set."""
    ok = tot = 0
    for s in snaps:
        for q, tg in s["targets"].items():
            tot += 1
            ok += s["preds"].get(q) in tg
    return ok, tot


def grip_stats(s: dict) -> dict:
    g0, g1 = (v >= GRIP_OPEN for v in s["grip_gt"])
    p1 = s["c"]["pred"][4] >= GRIP_OPEN
    evt = g0 != g1
    return {"grip_ok": p1 == g1, "evt": evt, "evt_ok": (p1 == g1) if evt else None}


def _plaus_hit(disp, d, r) -> bool:
    if math.hypot(disp[0], disp[1]) < V0.MIN_DISP_M:
        return False
    cd, cr = V0.cos_xy(disp, E0.unit_xy(d)), V0.cos_xy(disp, E0.unit_xy(r))
    return bool(cd > 0.5 and cd > cr)


def plaus_stats(s: dict) -> dict:
    """Plausible-edit pairs of one snapshot (sums): reference r = sector of disp_gt, edits = r +- 45 deg."""
    out = {k: 0.0 for k in P_KEYS}
    g, c = s["disp_gt"], s["c"]
    if math.hypot(g[0], g[1]) < XY_MIN_M:
        return out
    r = sector_xy(g[0], g[1])
    k = E0.DIR_XY8.index(r)
    nb = (E0.DIR_XY8[(k + 1) % 8], E0.DIR_XY8[(k - 1) % 8])
    ur, base = E0.unit_xy(r), np.asarray(c[f"xy:{r}"][:2], float)
    for d, d2 in (nb, nb[::-1]):
        disp = c[f"xy:{d}"][:3]
        e = E0.unit_xy(d) - ur
        e = e / np.linalg.norm(e)
        delta = np.asarray(disp[:2], float) - base
        h = _plaus_hit(disp, d, r)
        out["p_pairs"] += 1
        out["p_hits"] += h
        out["p_chance"] += 0.5 * (h + _plaus_hit(disp, d2, r))
        out["p_shift_hits"] += bool(np.linalg.norm(delta) >= V0.MIN_DISP_M
                                    and float(delta @ e) / np.linalg.norm(delta) > 0.5)
        out["p_shift_mm"] += 1000.0 * float(delta @ e)
        out["p_abs"] += V0.match_xy(disp, d)
    return out


def _p_pool(ps) -> dict:
    t = {k: float(sum(x[k] for x in ps)) for k in P_KEYS}
    n = t["p_pairs"]
    f = (lambda k: t[k] / n) if n else (lambda k: float("nan"))
    return {"p_pairs": int(n), "p_xy": f("p_hits"), "p_chance": f("p_chance"), "p_shift_rate": f("p_shift_hits"),
            "p_shift_mm_mean": f("p_shift_mm"), "p_abs_cos": f("p_abs")}


def _p_boot(ps_runs, n_boot: int, seed: int = 0) -> list:
    arr = {k: np.array([[x[k] for x in r] for r in ps_runs], float) for k in ("p_pairs", "p_hits")}
    rng = np.random.default_rng(seed)
    n = arr["p_pairs"].shape[1]
    v = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        v.append(arr["p_hits"][:, idx].sum() / max(arr["p_pairs"][:, idx].sum(), 1.0))
    return [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))]


def _g_pool(gs) -> dict:
    ev = [x["evt_ok"] for x in gs if x["evt"]]
    return {"grip_acc": float(np.mean([x["grip_ok"] for x in gs])) if gs else float("nan"),
            "grip_evt_n": len(ev), "grip_evt_acc": float(np.mean(ev)) if ev else float("nan")}


def load_runs(paths, n: int, ids_ref=None) -> list:
    """sr0_verdict.load of every seed file (+ checks: same snapshots in the same order, decision targets, near and
    gripper fields present; ids = ids_ref if given)."""
    runs = [V0.load(p, n, True) for p in paths]
    ids = [x["id"] for x in runs[0]]
    for p, r in zip(paths, runs):
        if [x["id"] for x in r] != ids:
            raise SystemExit(f"{p}: snapshots differ from {paths[0]}")
        if any(k not in x for x in r for k in ("targets", "near", "grip_gt")):
            raise SystemExit(f"{p}: records without decision targets / near / grip_gt")
    if ids_ref is not None and list(ids_ref) != ids:
        raise SystemExit(f"{paths[0]}: snapshots differ from the baseline")
    return runs


def dcfg_runs(runs_free, runs_near) -> list:
    """Per seed and snapshot: the free-space weight's record unless near contact (or unknown) -> the near weight's."""
    return [[f if b["near"] is False else b for f, b in zip(rf, rn)] for rf, rn in zip(runs_free, runs_near)]


def summarize(runs, n: int, boot: int = 10000) -> dict:
    st = [[V0.snap_stats(x, True) for x in r] for r in runs]
    ps = [[plaus_stats(x) for x in r] for r in runs]
    gs = [[grip_stats(x) for x in r] for r in runs]
    idx = np.arange(n)
    ci = V0.boot_ci(st, boot, 0)
    pb = _p_boot(ps, boot, 0)
    dc = [dec_counts(r) for r in runs]
    per = {}
    for k in range(len(runs)):
        pk = V0.pool([st[k]], idx)
        per[str(k)] = {**{m: pk[m] for m in ("a_xy", "chance_xy", "a_z", "rho_mean", "true_rate", "mse_pred",
                                             "mse_true")}, **_p_pool(ps[k]), **_g_pool(gs[k]),
                       "dec_acc": dc[k][0] / dc[k][1]}
    near = [x["near"] for x in runs[0]]
    strata = {}
    for name, flag in (("free", False), ("near", True), ("unknown", None)):
        sel = np.array([i for i in range(n) if near[i] is flag], int)
        if len(sel) == 0:
            strata[name] = {"n_snap": 0}
            continue
        pk = V0.pool(st, sel)
        strata[name] = {"n_snap": int(len(sel)), **{m: pk[m] for m in ("xy_pairs", "a_xy", "chance_xy", "a_z")},
                        **_p_pool([ps[k][i] for k in range(len(runs)) for i in sel]),
                        **_g_pool([gs[k][i] for k in range(len(runs)) for i in sel])}
    return {**V0.pool(st, idx), **_p_pool([x for r in ps for x in r]), **_g_pool([x for r in gs for x in r]),
            "lb": ci["a_xy"][0], "ub": ci["a_xy"][1], "p_lb": pb[0], "p_ub": pb[1], "ci95": ci,
            "n_seeds": len(runs), "dec_acc": sum(c for c, _ in dc) / sum(t for _, t in dc), "per_seed": per,
            "strata": strata}


def cell(paths, n: int, boot: int = 10000, ids_ref=None) -> dict:
    """Pooled metrics of one (arm, w) over its seed files."""
    runs = load_runs(paths, n, ids_ref)
    return {**summarize(runs, n, boot), "inputs": list(paths), "ids": [x["id"] for x in runs[0]]}


def checks(c: dict, base: dict, w: float, lat_ratio, metric: str = "a_xy") -> dict:
    """w = the cell's guidance weight (the free-space weight for a distance-CFG cell)."""
    if metric not in METRICS:
        raise ValueError(metric)
    if w != 1.0 and lat_ratio is None:
        raise ValueError("CFG cell without a latency measurement")
    lb, ch = METRICS[metric]
    dec_diff = c["dec_acc"] - base["dec_acc"]
    mse_rel = c["mse_pred"] / base["mse_pred"] - 1
    grip_diff = c["grip_acc"] - base["grip_acc"]
    r = {"target": c[metric] >= A_MIN - EPS, "lb": c[lb] > c[ch] + LB_MARGIN + EPS,
         "dec": dec_diff >= DEC_MIN - EPS, "mse": mse_rel <= MSE_MAX + EPS, "grip": grip_diff >= GRIP_MIN - EPS,
         "lat": w == 1.0 or lat_ratio <= LAT_MAX + EPS, "dec_diff": dec_diff, "mse_rel": mse_rel,
         "grip_diff": grip_diff, "lat_ratio": None if w == 1.0 else lat_ratio}
    r["ni"] = r["dec"] and r["mse"] and r["grip"] and r["lat"]
    r["all"] = r["target"] and r["lb"] and r["ni"]
    return r


def choose(cells: dict, metric: str) -> dict:
    """cells {(arm, w_sort): {metric value, 'checks': {metric: {...}}}} (distance CFG: w_sort = w_free + 0.5): the
    rule's verdict over the RULE_ARMS cells."""
    def rank(item):
        (arm, w), c = item
        return (-c[metric], w, RULE_ARMS.index(arm))
    rule = {k: v for k, v in cells.items() if k[0] in RULE_ARMS}
    ok = sorted(((k, v) for k, v in rule.items() if v["checks"][metric]["all"]), key=rank)
    if ok:
        return {"verdict": "ADOPT", "adopt": list(ok[0][0]), "best": list(ok[0][0]), "best_is_non_inferior": True}
    ni = sorted(((k, v) for k, v in rule.items() if v["checks"][metric]["ni"]), key=rank)
    best = ni[0] if ni else sorted(rule.items(), key=rank)[0]
    return {"verdict": "NOT_REACHED", "adopt": None, "best": list(best[0]), "best_is_non_inferior": bool(ni)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--latency", required=True, help="sr1b_latency.py output")
    ap.add_argument("--n", type=int, default=1200)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    man = json.load(open(a.manifest))
    lat = json.load(open(a.latency))
    lat_ratio = lat["full_p95_ratio_cfg_plain"] - 1
    base = cell(man["baseline"], a.n, a.boot)
    ids = base.pop("ids")
    cells, table, labels = {}, {}, {}

    def add(arm, label, w_eff, w_sort, c):
        c.pop("ids", None)
        c["checks"] = {m: checks(c, base, w_eff, None if w_eff == 1.0 else lat_ratio, m) for m in METRICS}
        c["w_eff"] = w_eff
        cells[(arm, w_sort)] = c
        labels[(arm, w_sort)] = f"{arm}@{label}"
        table[f"{arm}@{label}"] = c
    for arm, byw in man["arms"].items():
        for wt, paths in byw.items():
            add(arm, f"w{wt}", float(wt), float(wt), cell(paths, a.n, a.boot, ids_ref=ids))
        for wf, wn in DCFG:
            tf, tn = w_tag(wf), w_tag(wn)
            if tf in byw and tn in byw:
                rf = load_runs(byw[tf], a.n, ids)
                rn = load_runs(byw[tn], a.n, ids)
                c = {**summarize(dcfg_runs(rf, rn), a.n, a.boot), "inputs": {"free": byw[tf], "near": byw[tn]}}
                add(arm, f"d{tf}", wf, wf + 0.5, c)
    res = {}
    for m, key in (("a_xy", "stress"), ("p_xy", "plausible")):
        r = choose(cells, m)
        for k in ("adopt", "best"):
            r[k + "_label"] = None if r[k] is None else labels[tuple(r[k])]
        res[key] = r
    out = {"n": a.n, "baseline": base, "cells": table, "latency": {k: v for k, v in lat.items() if k != "ids"},
           "rule": {"A_MIN": A_MIN, "LB_MARGIN": LB_MARGIN, "DEC_MIN": DEC_MIN, "MSE_MAX": MSE_MAX,
                    "GRIP_MIN": GRIP_MIN, "LAT_MAX": LAT_MAX, "RULE_ARMS": list(RULE_ARMS),
                    "DCFG": [list(x) for x in DCFG]}, **res}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({"stress": res["stress"], "plausible": res["plausible"],
                      "cells": {k: [round(v["a_xy"], 4), round(v["p_xy"], 4), v["checks"]["a_xy"]["all"],
                                    v["checks"]["p_xy"]["all"]] for k, v in table.items()}}, indent=1))


if __name__ == "__main__":
    main()
