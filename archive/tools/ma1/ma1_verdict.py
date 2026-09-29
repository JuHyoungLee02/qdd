"""prereg_ma1 §6 verdict (fixed before any result): 2x2 cells {none, A = trace5 aux} x {none, O = history overlay},
every cell with the motion line (§83).

Inputs: per cell the `stageb_train predict` jsonl of its last/ checkpoint on the 300 val subset (seed 0: --pred;
seed 1 replication: --pred1), the transition flags (se2e_c1/transition_val.json), the latency json
(tools/ma1/ma1_latency.py), optionally the O cells evaluated WITHOUT the overlay (--pred-nooverlay).
  python tools/ma1/ma1_verdict.py --pred none+none=F A+none=F none+O=F A+O=F [--pred1 ...] \
      [--pred-nooverlay none+O=F A+O=F] --trans F --lat F --out JSON
Main effect of a factor = mean over the other factor's two levels of (on - off). Seed-0 rule per factor: overall acc
main effect >= +0.02 AND transition-stratum main effect >= -0.01 AND decide FULL p95 increase <= 10 %
(A: (A+none)/(none+none) - 1, O: (none+O)/(none+none) - 1); CMP_EPS 1e-12. A factor passing the seed-0 rule is
replicated with seed 1 (all four cells at seed 1) and FINALLY adopted <=> the two-seed MEAN main effects pass (1)
and (2) (latency (3) from the seed-0 measurement); a factor failing seed 0 is not adopted (no seed 1). O not adopted
-> the VLA-input overlay is dropped; only the Astra-image overlay (design §13) stays. Reported, outside the rule:
per-source (RB1 / RB2) accuracy and main effects, per question, NLL, interaction, overlay dependency (O cell accuracy
with minus without the overlay; > 0.05 = warning), snapshot-cluster bootstrap (10,000, seed 0, 95 % percentile).
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np

CELLS = ("none+none", "A+none", "none+O", "A+O")
QUESTIONS = ("dir_xy", "dir_z", "mag_coarse")
SOURCES = ("RB1", "RB2")
MIN_GAIN, MAX_TRANS_DROP, MAX_P95_INC = 0.02, 0.01, 0.10
DEPENDENCY_WARN = 0.05
CMP_EPS = 1e-12  # §74 / §77 supplement 2
N_BOOT, SEED = 10_000, 0


def _ge(x, t):
    return x >= t - CMP_EPS * max(1.0, abs(t))


def _le(x, t):
    return x <= t + CMP_EPS * max(1.0, abs(t))


def _gt(x, t):
    return x > t + CMP_EPS * max(1.0, abs(t))


def load_items(path):
    rows = [json.loads(x) for x in open(path)]
    summ = [r for r in rows if r.get("event") == "summary"]
    items = [r for r in rows if r.get("event") == "item"]
    for r in items:
        lp = [r["lp"][t] for t in r["target"]]
        m = max(lp)
        r["nll"] = -(m + math.log(sum(math.exp(v - m) for v in lp)))
    return items, (summ[-1] if summ else None)


def _agg(xs):
    return {"n_items": len(xs), "n_snap": len({r["key"] for r in xs}),
            "acc": float(np.mean([r["correct"] for r in xs])) if xs else None,
            "nll": float(np.mean([r["nll"] for r in xs])) if xs else None}


def metrics(items, flags):
    out = {"all": _agg(items), "transition": _agg([r for r in items if flags[r["key"]]["transition"]]),
           "steady": _agg([r for r in items if not flags[r["key"]]["transition"]])}
    for q in QUESTIONS:
        xs = [r for r in items if r["question"] == q]
        out[f"q_{q}"] = _agg(xs)
        out[f"q_{q}_item_transition"] = _agg([r for r in xs if flags[r["key"]]["per_q"][q]])
    out["per_source"] = {}
    for s in SOURCES:
        xs = [r for r in items if r["key"].split("_")[0] == s]
        out["per_source"][s] = {"all": _agg(xs), "transition": _agg([r for r in xs if flags[r["key"]]["transition"]])}
    return out


def effects(get):
    return {"A": 0.5 * ((get("A+none") - get("none+none")) + (get("A+O") - get("none+O"))),
            "O": 0.5 * ((get("none+O") - get("none+none")) + (get("A+O") - get("A+none"))),
            "AxO": (get("A+O") - get("none+O")) - (get("A+none") - get("none+none"))}


def main_effects(m, stratum, key="acc"):
    return effects(lambda c: m[c][stratum][key])


def bootstrap(items_by_cell, flags):
    keys = sorted({r["key"] for r in items_by_cell[CELLS[0]]})
    idx = {k: i for i, k in enumerate(keys)}
    acc = {c: np.zeros(len(keys)) for c in CELLS}
    cnt = np.zeros(len(keys))
    for c in CELLS:
        for r in items_by_cell[c]:
            acc[c][idx[r["key"]]] += r["correct"]
    for r in items_by_cell[CELLS[0]]:
        cnt[idx[r["key"]]] += 1
    trans = np.array([flags[k]["transition"] for k in keys])
    rng = np.random.default_rng(SEED)
    out = {}
    for name, mask in (("all", np.ones(len(keys), bool)), ("transition", trans)):
        ks = np.flatnonzero(mask)
        draws = {"A": [], "O": [], "AxO": []}
        for _ in range(N_BOOT):
            b = rng.choice(ks, len(ks), replace=True)
            a = {c: acc[c][b].sum() / cnt[b].sum() for c in CELLS}
            for f, v in effects(lambda c: a[c]).items():
                draws[f].append(v)
        out[name] = {k: [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] for k, v in draws.items()}
    return out


def _cells(paths, flags):
    if set(paths) != set(CELLS):
        raise SystemExit(f"cells {sorted(paths)} != {CELLS}")
    items, m = {}, {}
    for c in CELLS:
        items[c], summ = load_items(paths[c])
        m[c] = metrics(items[c], flags)
        if summ is not None:  # the item records reproduce evaluate()'s aggregate
            assert abs(m[c]["all"]["acc"] - summ["dec_acc"]) < 1e-9, c
            assert abs(m[c]["all"]["nll"] - summ["dec"]) < 1e-5, c
    ks = {c: sorted({r["key"] for r in items[c]}) for c in CELLS}
    assert all(v == ks[CELLS[0]] for v in ks.values()), "cells evaluated on different val keys"
    return items, m


def rule(m, p95_inc):
    eff = {s: main_effects(m, s) for s in ("all", "transition")}
    out = {}
    for f in ("A", "O"):
        c1, c2, c3 = _ge(eff["all"][f], MIN_GAIN), _ge(eff["transition"][f], -MAX_TRANS_DROP), \
            _le(p95_inc[f], MAX_P95_INC)
        out[f] = {"overall_main_effect": eff["all"][f], "transition_main_effect": eff["transition"][f],
                  "p95_increase": p95_inc[f], "c1_gain": c1, "c2_transition": c2, "c3_latency": c3,
                  "pass": bool(c1 and c2 and c3)}
    return out


def _parse(xs):
    return dict(x.split("=", 1) for x in xs) if xs else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", nargs=4, required=True, help="cell=path, seed 0")
    ap.add_argument("--pred1", nargs=4, default=None, help="cell=path, seed 1 (replication of passing factors)")
    ap.add_argument("--pred-nooverlay", nargs="+", default=None, help="O cells evaluated without the overlay")
    ap.add_argument("--trans", required=True)
    ap.add_argument("--lat", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    flags = json.load(open(a.trans))["flags"]
    items, m = _cells(_parse(a.pred), flags)
    lat = json.load(open(a.lat))["formats"]
    p95 = {c: lat[c]["full_p95"] for c in CELLS}
    p95_inc = {"A": p95["A+none"] / p95["none+none"] - 1, "O": p95["none+O"] / p95["none+none"] - 1}
    v0 = rule(m, p95_inc)
    out = {"cells": m, "latency": lat, "p95_increase": p95_inc, "seed0": v0,
           "main_effects_acc": {s: main_effects(m, s) for s in ("all", "transition", "steady")},
           "main_effects_nll": {s: main_effects(m, s, "nll") for s in ("all", "transition", "steady")},
           "main_effects_per_source": {s: {st: effects(lambda c: m[c]["per_source"][s][st]["acc"])
                                           for st in ("all", "transition")} for s in SOURCES},
           "bootstrap_acc_95": bootstrap(items, flags),
           "seed1_needed": [f for f in ("A", "O") if v0[f]["pass"]], "seed1": None, "final": None,
           "rule": {"min_gain": MIN_GAIN, "max_transition_drop": MAX_TRANS_DROP, "max_p95_increase": MAX_P95_INC,
                    "cmp_eps": CMP_EPS, "dependency_warn": DEPENDENCY_WARN},
           "n_val_snapshots": len({r["key"] for r in items[CELLS[0]]})}
    if a.pred1:
        items1, m1 = _cells(_parse(a.pred1), flags)
        assert sorted({r["key"] for r in items1[CELLS[0]]}) == sorted({r["key"] for r in items[CELLS[0]]})
        v1 = rule(m1, p95_inc)
        out["cells_seed1"], out["seed1"] = m1, v1
        fin = {}
        for f in ("A", "O"):
            if not v0[f]["pass"]:
                fin[f] = {"adopt": False, "reason": "seed0 rule not passed"}
                continue
            e_all = 0.5 * (v0[f]["overall_main_effect"] + v1[f]["overall_main_effect"])
            e_tr = 0.5 * (v0[f]["transition_main_effect"] + v1[f]["transition_main_effect"])
            c1, c2, c3 = _ge(e_all, MIN_GAIN), _ge(e_tr, -MAX_TRANS_DROP), v0[f]["c3_latency"]
            fin[f] = {"overall_main_effect_2seed": e_all, "transition_main_effect_2seed": e_tr, "c1_gain": c1,
                      "c2_transition": c2, "c3_latency": c3, "adopt": bool(c1 and c2 and c3),
                      "reason": "two-seed mean rule"}
        out["final"] = fin
    if out["final"] is not None:
        o_adopt = out["final"]["O"]["adopt"]
    else:
        o_adopt = None if v0["O"]["pass"] else False
    out["vla_overlay"] = ("drop: the VLA-input overlay is not used; only the Astra-image overlay (design §13) stays"
                          if o_adopt is False else "keep (O adopted)" if o_adopt else "pending seed-1 replication")
    if a.pred_nooverlay:
        dep = {}
        for c, p in _parse(a.pred_nooverlay).items():
            it, _ = load_items(p)
            mm = metrics(it, flags)
            d = m[c]["all"]["acc"] - mm["all"]["acc"]
            dep[c] = {"acc_with": m[c]["all"]["acc"], "acc_without": mm["all"]["acc"], "drop": d,
                      "drop_transition": m[c]["transition"]["acc"] - mm["transition"]["acc"],
                      "warn": bool(_gt(d, DEPENDENCY_WARN))}
        out["overlay_dependency"] = dep
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({"seed0": v0, "final": out["final"], "vla_overlay": out["vla_overlay"]}, indent=1))


if __name__ == "__main__":
    main()
