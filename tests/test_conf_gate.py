"""E-CONF path-reproduction gate G1 (docs/stage3/prereg_conf.md §4)."""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G = _load("conf_gate", ("tools", "conf", "conf_gate.py"))


def _mine(i, pred="x", mse=0.01, m=1.0):
    return {"id": f"s{i}", "mse": mse, "q": {"qa": {"lp": {"x": 0.0, "y": -m}, "pred": pred, "target": ["x"]}}}


def test_ref_from_nov0_meta_and_sr0_records():
    r = G.ref_record({"id": "a", "preds": {"qa": "x"}, "margin": {"qa": 1.5}, "mse": 0.2})
    assert r == {"preds": {"qa": "x"}, "mse": 0.2, "margin": {"qa": 1.5}}
    r = G.ref_record({"event": "snap", "id": "b", "preds": {"qa": "y"}, "c": {"pred": [0, 0, 0, 1, 1, 0.3, 0]}})
    assert r == {"preds": {"qa": "y"}, "mse": 0.3, "margin": None}


def test_gate_passes_on_identical_and_fails_on_drift():
    mine = [_mine(i) for i in range(200)]
    ref = {f"s{i}": {"preds": {"qa": "x"}, "mse": 0.01, "margin": {"qa": 1.0}} for i in range(200)}
    g = G.gate(mine, ref)
    assert g["pass"] and g["n_overlap"] == 200 and g["pred_agree"] == 1.0
    assert g["mse_ratio"] == pytest.approx(1.0) and g["margin_med_abs"] == pytest.approx(0.0)
    bad = [_mine(i, mse=0.0103) for i in range(200)]
    assert not G.gate(bad, ref)["pass"]  # median relative difference 0.03 > 0.01
    wrong = [_mine(i, pred="y" if i < 3 else "x") for i in range(200)]
    assert not G.gate(wrong, ref)["pass"]  # agreement 0.985 < 0.99


def test_gate_needs_overlap():
    g = G.gate([_mine(0)], {"zz": {"preds": {"qa": "x"}, "mse": 0.1, "margin": None}})
    assert g["n_overlap"] == 0 and not g["pass"]
