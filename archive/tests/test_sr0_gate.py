"""E-SR0 path gate G1 (prereg_sr0 §4): sr0_eval reproduces the earlier evaluations of the same checkpoints."""
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sr0_gate", os.path.join(ROOT, "tools", "sr0", "sr0_gate.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def _w(path, recs):
    with open(path, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def _sr0(path, n=3, mse=0.03, pred="plus_x", disp=(0.01, 0.0, 0.0)):
    recs = [{"event": "snap", "i": i, "id": f"id{i}", "key": f"k{i}", "preds": {"dir_xy": pred, "dir_z": "up"},
             "c": {"true": [0, 0, 0, 0, 0, mse], "pred": list(disp) + [0, 0, mse]}} for i in range(n)]
    _w(path, recs + [{"event": "summary", "n": n}])


def test_se2e_gate(tmp_path):
    p, q = tmp_path / "s.jsonl", tmp_path / "m.jsonl"
    _sr0(p, mse=0.0330)
    items = [{"event": "item", "key": f"k{i}", "question": qq, "pred": pr} for i in range(5)
             for qq, pr in (("dir_xy", "plus_x"), ("dir_z", "up"))]
    _w(q, items + [{"event": "summary", "sample_mse_norm": 0.03}])
    r = G.gate_se2e(str(p), str(q))
    assert r["pass"] and r["n_items"] == 6 and r["pred_agree"] == 1.0 and abs(r["mse_rel"] - 0.10) < 1e-9
    _sr0(p, mse=0.0331)
    assert not G.gate_se2e(str(p), str(q))["pass"]  # MSE 10.3 % off
    _sr0(p, pred="minus_x")
    assert not G.gate_se2e(str(p), str(q))["pass"]  # predictions differ


def test_r2_gate(tmp_path):
    p, q = tmp_path / "s.jsonl", tmp_path / "e.jsonl"
    _sr0(p, disp=(0.0105, 0.0, 0.0))
    ev = [{"event": "item", "id": f"id{i}", "cond": c, "preds": {"dir_xy": "plus_x", "dir_z": "up"},
           "disp": [0.01, 0.0, 0.0]} for i in range(4) for c in ("none",)]
    _w(q, ev + [{"event": "summary"}])
    r = G.gate_r2(str(p), str(q))
    assert r["pass"] and r["n_snap"] == 3 and abs(r["disp_diff_median_m"] - 0.0005) < 1e-9
    _sr0(p, disp=(0.0115, 0.0, 0.0))
    assert not G.gate_r2(str(p), str(q))["pass"]  # 1.5 mm > 1 mm


def test_missing_reference_fails(tmp_path):
    p, q = tmp_path / "s.jsonl", tmp_path / "e.jsonl"
    _sr0(p)
    _w(q, [{"event": "summary"}])
    with pytest.raises(SystemExit):
        G.gate_r2(str(p), str(q))
