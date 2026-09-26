"""E-SR1c gates (prereg_sr1c §0): G-br pure parts (tools/sr1c/replay_check.py) and G-a / G0 / G1 / G2
(tools/sr1c/sr1c_gate.py)."""
import importlib.util
import json
import os

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mod(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R = _mod("replay_check", ("tools", "sr1c", "replay_check.py"))
G = _mod("sr1c_gate", ("tools", "sr1c", "sr1c_gate.py"))


def test_pick_whole_snapshots_until_n():
    by = {("dr", "t", "P0", s, 10): [0] * 4 for s in range(20)}
    keys = R.pick(by, 10, seed=0)
    assert len(keys) == 3 and len(set(keys)) == 3
    assert keys == R.pick(by, 10, seed=0) and keys != R.pick(by, 10, seed=1)


def test_branch_metrics():
    u = np.array([1.0, 0.0, 0.0])
    m = R.branch_metrics([0.04, 0, 0], u, [0.4, 0, 0.2], [0.441, 0.001, 0.2], [[0.4, 0, 0.2], [0.441, 0, 0.2]], set(),
                         0.0, 0.2)
    assert m["track_err_mm"] == pytest.approx(np.hypot(1, 1), abs=1e-3) and m["dir_ok"]
    assert not m["table"] and not m["object"] and not m["near_end"]
    m = R.branch_metrics([0.04, 0, 0], u, [0.4, 0, 0.2], [0.4, 0.02, 0.2], [[0.4, 0, 0.02]], {"o8"}, 0.0, 0.04)
    assert not m["dir_ok"] and m["table"] and m["object"] and m["near_end"]
    assert R.branch_metrics([0.04, 0, 0], u, [0, 0, 0], [0.04, 0, 0], [[0, 0, 0.1]], set(), 0.004, 0.2)["object"]


def _rec(t=2.0, **kw):
    return {"track_err_mm": t, "table": False, "object": False, "dir_ok": True, "near_end": False, **kw}


def test_gbr_rule():
    recs = [_rec(2.0)] * 9 + [_rec(7.0)]
    assert R.gate(recs)["pass"]
    assert not R.gate([_rec(3.5)] * 10)["pass"]
    assert not R.gate([_rec(2.0)] * 8 + [_rec(9.0)] * 2)["pass"]
    assert not R.gate([_rec(2.0)] * 9 + [_rec(2.0, table=True)])["pass"]
    assert not R.gate([_rec(2.0)] * 9 + [_rec(2.0, dir_ok=False)])["pass"]
    gs = {"by_dir": {"plus_x": 10, "minus_x": 4}, "rejected_by_dir": {"minus_x": 5}}
    assert not R.gate(recs, gs)["pass"] and R.gate(recs, {"by_dir": {"plus_x": 10}, "rejected_by_dir": {}})["pass"]


def _snap(i, stratum, dist, dist_hat, a_priv, a_hat):
    return {"event": "snap", "id": f"s{i}", "stratum": stratum, "dist_priv": dist, "dist_hat": dist_hat,
            "a_priv": a_priv, "a_hat": a_hat, "phase": "approach"}


def test_ga_rule():
    ok = [_snap(i, "near", 0.08, 0.085, 0.0, 0.0) for i in range(20)] + [_snap(99, "far", 0.3, 0.3, 1.0, 1.0)]
    r = G.ga(ok)
    assert r["pass"] and r["band_n"] == 20 and r["err_median_m"] == pytest.approx(0.005)
    bad = [_snap(i, "near", 0.08, 0.10, 0.0, 0.0) for i in range(20)]
    assert not G.ga(bad)["pass"]  # median error 2 cm
    mis = [_snap(i, "near", 0.08, 0.08, 0.0, 0.0) for i in range(18)] + \
        [_snap(50 + i, "near", 0.04, 0.07, 0.0, 0.4) for i in range(2)]
    r = G.ga(mis)
    assert r["near_misclass"] == pytest.approx(0.1) and not r["pass"]


def test_g0_rule():
    log = [{"event": "sr1c_branches", "n_rows": 1000, "joined": 1000, "missing": 0}] + \
        [{"event": "train", "step": s, "n_branch": 8, "fm_branch": 0.5} for s in range(1, 11)]
    assert G.g0(log, n_registered=1000, batch=8)["pass"]
    assert not G.g0(log, n_registered=1100, batch=8)["pass"]
    log2 = log[:1] + [{"event": "train", "step": 1, "n_branch": 4, "fm_branch": 0.5}]
    assert not G.g0(log2, n_registered=1000, batch=8)["pass"]


def test_g2_rule():
    log = [{"event": "train", "step": 1, "total": 1.0, "elapsed_s": 10.0},
           {"event": "train", "step": 2000, "total": 0.5, "elapsed_s": 4000.0}]
    assert G.g2(log, limit_s=4920)["pass"]
    assert not G.g2(log, limit_s=3000)["pass"]
    log.append({"event": "train", "step": 2001, "total": float("nan"), "elapsed_s": 4001.0})
    assert not G.g2(log, limit_s=4920)["pass"]


def test_config_identity_except_the_sr1c_options():
    c0 = {"batch": 8, "max_steps": 2000, "seed": 0, "lr": 1e-4, "run": "c0", "ma2": "c0", "out_root": "/a"}
    c1 = {**c0, "run": "c1", "out_root": "/b", "cf_branch": "/br", "cf_frac": 0.5, "dec_cond": "none"}
    assert G.config_diff(c0, c1) == {}
    assert G.config_diff(c0, {**c1, "batch": 4}) == {"batch": (8, 4)}
