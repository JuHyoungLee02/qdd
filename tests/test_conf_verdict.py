"""E-CONF verdict rules and pipeline (docs/stage3/prereg_conf.md §5)."""
import importlib.util
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = _load("conf_verdict", ("tools", "conf", "conf_verdict.py"))
L = V.L


# ------------------------------------------------------------------------------------------ thresholds
def test_thresholds_fixed():
    assert V.TH == {"auroc": 0.75, "reduction90": 0.30, "transfer_recall": 0.85, "lat_p95_ms": 5.0,
                    "imp_delta": 0.03, "imp_lat_p95_ms": 5.0}
    assert V.N_BOOT == 10000 and V.LAT_S == 9.3 and not hasattr(V, "HOLD_S")


def _m(a=0.8, r=0.4, t=0.9, lat=0.01):
    return {"auroc": a, "reduction90": r, "transfer_recall": t, "lat_p95_ms": lat}


def test_part_v_needs_every_condition():
    assert V.part_v(_m())
    assert not V.part_v(_m(a=0.7499))
    assert V.part_v(_m(a=0.75, r=0.30, t=0.85, lat=5.0))
    assert not V.part_v(_m(r=0.29))
    assert not V.part_v(_m(t=0.84))
    assert not V.part_v(_m(lat=5.1))


def test_part_i_needs_delta_holm_and_latency():
    assert V.part_i({"delta": 0.03, "holm_reject": True}, 1.0)
    assert not V.part_i({"delta": 0.029, "holm_reject": True}, 1.0)
    assert not V.part_i({"delta": 0.05, "holm_reject": False}, 1.0)
    assert not V.part_i({"delta": 0.05, "holm_reject": True}, 5.5)


def test_decide_prefers_passing_improvement_then_base():
    pv = {"r2": {"base": _m(), "lr": _m()}, "se2e": {"base": _m(), "lr": _m()}}
    imp = {"lr": {"r2": {"delta": 0.05, "holm_reject": True}, "se2e": {"delta": 0.04, "holm_reject": True}}}
    lat = {"lr": 0.1}
    assert V.decide(pv, imp, lat)["verdict"] == "ADOPT_lr"
    imp["lr"]["se2e"]["holm_reject"] = False
    assert V.decide(pv, imp, lat)["verdict"] == "ADOPT_base"
    pv["se2e"]["base"] = _m(a=0.6)
    d = V.decide(pv, imp, lat)
    assert d["verdict"] == "NONE" and d["pass_v"]["base"] == {"r2": True, "se2e": False}


def test_decide_improvement_must_also_pass_part_v():
    pv = {"r2": {"base": _m(), "lr": _m(r=0.2)}, "se2e": {"base": _m(), "lr": _m()}}
    imp = {"lr": {"r2": {"delta": 0.05, "holm_reject": True}, "se2e": {"delta": 0.05, "holm_reject": True}}}
    assert V.decide(pv, imp, {"lr": 0.1})["verdict"] == "ADOPT_base"


def test_decide_picks_largest_min_delta():
    pv = {d: {s: _m() for s in ("base", "lr", "temp_min")} for d in ("r2", "se2e")}
    imp = {"lr": {"r2": {"delta": 0.09, "holm_reject": True}, "se2e": {"delta": 0.04, "holm_reject": True}},
           "temp_min": {"r2": {"delta": 0.05, "holm_reject": True}, "se2e": {"delta": 0.05, "holm_reject": True}}}
    assert V.decide(pv, imp, {"lr": 0.1, "temp_min": 0.1})["verdict"] == "ADOPT_temp_min"


# ------------------------------------------------------------------------------------------ pipeline
def _recs(n_ep, seed, prefix, noise=1.0):
    rng = np.random.default_rng(seed)
    out = []
    for e in range(n_ep):
        for k in range(12):
            m1, m2 = rng.exponential(2.0), rng.exponential(1.5)
            ok1 = rng.random() < 1 / (1 + math.exp(-2 * m1 / noise))
            ok2 = rng.random() < 1 / (1 + math.exp(-2 * m2 / noise))
            out.append({"id": f"{prefix}{e}_k{k}", "ep": f"{prefix}{e}", "t": 0.5 * k, "kind": "RB1",
                        "variant": "standard", "task": "mug_tray", "mse": float(rng.exponential(0.02)),
                        "disp": float(rng.exponential(0.01) * (1 + 2 * (not ok2))),
                        "q": {"qa": {"lp": {"x": 0.0, "y": -m1}, "target": ["x"] if ok1 else ["y"], "pred": "x"},
                              "qb": {"lp": {"u": 0.0, "v": -m2}, "target": ["u"] if ok2 else ["v"], "pred": "u"}}})
    return out


def test_oof_uses_the_other_half_fit():
    recs = _recs(40, 0, "RB1_ep")
    oof = V.oof(recs)
    h = np.array([L.half_of(r["ep"]) for r in recs])
    other = [r for r in recs if L.half_of(r["ep"]) == 1]
    f1 = L.fit(other)
    i0 = int(np.flatnonzero(h == 0)[0])
    assert oof["scores"]["lr"][i0] == pytest.approx(L.risk(recs[i0], "lr", f1))
    assert oof["y"][i0] == L.labels([recs[i0]], f1["mse_thr"])[0]


def test_compute_runs_and_reports_every_block():
    data = {"r2": {"c0": (_recs(30, 1, "cal"), _recs(20, 2, "tst")), "c1": (_recs(30, 3, "cal"), _recs(20, 4, "tst"))},
            "se2e": {"s1": _recs(40, 5, "RB1_ep"), "s2": _recs(40, 6, "RB1_ep")}}
    res = V.compute(data, n_boot=50, lat_ms={"r2": 3.0, "se2e": 3.0}, unseen=None)
    for d in ("r2", "se2e"):
        blk = res[d]
        assert set(blk["auroc"]) == set(L.SCORES)
        assert {"point", "ci"} <= set(blk["auroc"]["base"])
        assert set(blk["improve"]) == set(L.SCORES) - {"base"}
        assert "transfer" in blk and "per_question" in blk and "ece" in blk and "runtime" in blk
    assert res["rules"]["verdict"] in {"NONE"} | {f"ADOPT_{s}" for s in L.SCORES}
