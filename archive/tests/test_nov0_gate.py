"""E-NOV0 path gate G1 (docs/stage3/prereg_nov0.md §4): our eval decisions / chunk MSE against E-MA2 / E-SR0 records."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G = _load("nov0_gate", ("tools", "nov0", "nov0_gate.py"))
P = {"dir_xy": "plus_x", "dir_z": "up"}


def _ours(i, preds=P, mse=0.03):
    return {"id": f"dr/mug_tray/P0/ep100{i:02d}/k0", "preds": preds, "mse": mse}


def test_g1_pass_on_matching_records():
    ours = [_ours(i) for i in range(10)]
    ma2 = [{"event": "item", "id": o["id"], "cond": "none", "preds": P} for o in ours]
    ma2 += [{"event": "item", "id": ours[0]["id"], "cond": "e90", "preds": {"dir_xy": "minus_x", "dir_z": "up"}}]
    sr0 = [{"event": "snap", "id": o["id"], "c": {"pred": [0, 0, 0, 1, 1, 0.0301]}} for o in ours]
    r = G.gate_g1(ours, ma2, sr0)
    assert r["pass"] and r["agree"] == 1.0 and r["n_overlap"] == 10
    assert abs(r["mse_ratio"] - 0.03 / 0.0301) < 1e-12
    assert abs(r["mse_med_rel"] - 0.0001 / 0.0301) < 1e-9


def test_g1_same_noise_needs_per_snapshot_match():
    """Same flow-noise draws (E-SR0 numbering): the mean can match while single chunks differ -> fail."""
    ours = [_ours(i, mse=0.02 if i % 2 else 0.04) for i in range(10)]
    ma2 = [{"event": "item", "id": o["id"], "cond": "none", "preds": P} for o in ours]
    sr0 = [{"event": "snap", "id": o["id"], "c": {"pred": [0, 0, 0, 1, 1, 0.04 if i % 2 else 0.02]}}
           for i, o in enumerate(ours)]
    r = G.gate_g1(ours, ma2, sr0)
    assert abs(r["mse_ratio"] - 1.0) < 1e-12 and not r["pass"]


def test_g1_fails_on_disagreement_or_mse_drift():
    ours = [_ours(i) for i in range(10)]
    ma2 = [{"event": "item", "id": o["id"], "cond": "none", "preds": P} for o in ours]
    sr0 = [{"event": "snap", "id": o["id"], "c": {"pred": [0, 0, 0, 1, 1, 0.03]}} for o in ours]
    bad = [dict(o, preds={"dir_xy": "minus_x", "dir_z": "up"}) if i == 0 else o for i, o in enumerate(ours)]
    assert not G.gate_g1(bad, ma2, sr0)["pass"]  # 19/20 = 0.95 < 0.99
    drift = [dict(o, mse=0.04) for o in ours]
    assert not G.gate_g1(drift, ma2, sr0)["pass"]
    assert not G.gate_g1(ours[:0], ma2, sr0)["pass"]  # no overlap
