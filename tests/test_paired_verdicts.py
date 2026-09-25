"""E-CAM3 / E-MA3 verdicts (prereg_cam3 §5, prereg_ma3 §5): paired two-seed effects against the motion-confirm
baseline, snapshot-cluster bootstrap, rule boundaries (CMP_EPS), input checks (P25)."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "se2e"))
import paired_verdict as PV  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "cam3"))
import cam3_verdict as CV  # noqa: E402

QS = ("dir_xy", "dir_z", "mag_coarse")


def _write(path, n, correct_fn, mse=None):
    with open(path, "w") as f:
        for i in range(n):
            for q in QS:
                c = bool(correct_fn(i, q))
                lp = {"a": -0.1, "b": -2.4} if c else {"a": -2.4, "b": -0.1}
                f.write(json.dumps({"event": "item", "key": f"RB{1 + i % 2}_ep{i}_k0", "question": q, "target": ["a"],
                                    "pred": "a" if c else "b", "correct": c, "lp": lp}) + "\n")
            if mse is not None:
                f.write(json.dumps({"event": "chunk", "key": f"RB{1 + i % 2}_ep{i}_k0", "mse_n": mse(i),
                                    "mae_q": 0.0, "fm": 0.0, "mse_pred": mse(i)}) + "\n")
    return str(path)


def _flags(path, n):
    fl = {f"RB{1 + i % 2}_ep{i}_k0": {"transition": i % 3 == 0, "per_q": {q: i % 3 == 0 for q in QS}}
          for i in range(n)}
    json.dump({"flags": fl}, open(path, "w"))
    return str(path)


def test_rules_at_the_boundaries():
    assert CV.rule(0.02, 1e-9, -0.01, 1.10)["adopt"]
    assert not CV.rule(0.02 - 1e-6, 0.01, 0.0, 1.0)["adopt"]
    assert not CV.rule(0.03, 0.0, 0.0, 1.0)["adopt"]  # lower bound strictly > 0
    assert not CV.rule(0.03, 0.01, -0.0101, 1.0)["adopt"]
    assert not CV.rule(0.03, 0.01, 0.0, 1.1001)["adopt"]


def test_paired_effects_and_bootstrap(tmp_path):
    n = 60
    fl = _flags(tmp_path / "f.json", n)
    p = {"none_s1": _write(tmp_path / "a", n, lambda i, q: i % 2 == 0),
         "x_s1": _write(tmp_path / "b", n, lambda i, q: i % 2 == 0 or i % 5 == 1),
         "none_s2": _write(tmp_path / "c", n, lambda i, q: i % 2 == 0),
         "x_s2": _write(tmp_path / "d", n, lambda i, q: i % 2 == 0 or i % 5 == 1)}
    items, m = PV.load_runs(p, json.load(open(fl))["flags"], "x", n_snap=n)
    per, pooled, spread = PV.effects(m, "x")
    assert pooled["all"] == pytest.approx(6 / 60) and spread["all"] == 0
    boot = PV.bootstrap_acc(items, json.load(open(fl))["flags"], "x", n_boot=200)
    assert boot["all"][0] > 0 and boot["all"][0] <= pooled["all"] <= boot["all"][1]


def test_load_refuses_wrong_size_or_duplicates(tmp_path):
    n = 10
    fl = json.load(open(_flags(tmp_path / "f.json", n)))["flags"]
    p = {k: _write(tmp_path / k, n, lambda i, q: True) for k in ("none_s1", "x_s1", "none_s2", "x_s2")}
    with pytest.raises(AssertionError):
        PV.load_runs(p, fl, "x", n_snap=11)
    with open(p["x_s2"], "a") as f:
        f.write(json.dumps({"event": "item", "key": "RB1_ep0_k0", "question": "dir_xy", "target": ["a"], "pred": "a",
                            "correct": True, "lp": {"a": -0.1, "b": -2.4}}) + "\n")
    with pytest.raises(AssertionError):
        PV.load_runs(p, fl, "x", n_snap=n)


def test_relative_chunk_reduction(tmp_path):
    n = 40
    p = {"none_s1": _write(tmp_path / "a", n, lambda i, q: True, lambda i: 0.04),
         "kv_s1": _write(tmp_path / "b", n, lambda i, q: True, lambda i: 0.036),
         "none_s2": _write(tmp_path / "c", n, lambda i, q: True, lambda i: 0.05),
         "kv_s2": _write(tmp_path / "d", n, lambda i, q: True, lambda i: 0.04 + 0.001 * (i % 2))}
    ch = {k: PV.load_chunks(v) for k, v in p.items()}
    r = PV.rel_reduction(ch, "kv", "mse_n", n_boot=200)
    assert r["per_seed"]["s1"] == pytest.approx(0.1) and r["per_seed"]["s2"] == pytest.approx(1 - 0.0405 / 0.05)
    assert r["pooled"] == pytest.approx(0.5 * (0.1 + 1 - 0.0405 / 0.05))
    assert r["boot_95"][0] <= r["pooled"] <= r["boot_95"][1]
