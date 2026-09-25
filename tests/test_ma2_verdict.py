"""E-MA2 verdict (prereg_ma2 §6): rule boundaries, compliance scoring and input checks."""
import importlib.util
import json
import os

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("ma2_verdict", os.path.join(ROOT, "tools", "ma2", "ma2_verdict.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


def _d(c0=0.3, c1=0.6, c2=0.7, a0=0.80, a1=0.80, a2=0.79, l0=0.080, l1=0.081, l2=0.0891):
    return V.decide({"c0": c0, "c1": c1, "c2": c2}, {"c0": a0, "c1": a1, "c2": a2}, {"c0": l0, "c1": l1, "c2": l2})


def test_c2_at_the_exact_boundaries():
    r = _d()  # +0.10, -0.01, +10 %
    assert r["verdict"] == "C2" and all(r["c2_conditions"].values())


@pytest.mark.parametrize("kw", [{"c2": 0.6999}, {"a2": 0.7899}, {"l2": 0.08911}])
def test_c2_fails_just_outside_and_c1_takes_over(kw):
    r = _d(**kw)
    assert r["verdict"] == "C1"


def test_both_below_0_6_is_none_even_with_a_big_gap():
    r = _d(c1=0.40, c2=0.5999)
    assert r["verdict"] == "NONE" and r["both_below_0.6"]


def test_c1_needs_its_own_conditions():
    assert _d(c2=0.65, a1=0.7899)["verdict"] == "NONE"
    assert _d(c2=0.65, l1=0.08801)["verdict"] == "NONE"
    assert _d(c1=0.5999, c2=0.65)["verdict"] == "NONE"  # c2 >= 0.6 but not +0.10 over c1, c1 < 0.6


def test_cos_xy():
    assert V.cos_xy([1, 0, 5], [2, 0, -1]) == pytest.approx(1.0)
    assert V.cos_xy([0, 0, 1], [1, 0, 0]) == -2.0


def _write(path, ids, cond, fn):
    with open(path, "w") as f:
        for j, i in enumerate(ids):
            for cn in ["none"] + (["e0", "e90", "e180"] if cond != "c0" else []):
                f.write(json.dumps(fn(i, cn)) + "\n")
        f.write(json.dumps({"event": "summary", "ma2": cond}) + "\n")


def test_per_snapshot_scores_a_following_model(tmp_path):
    from harvest.train.r2_ma2 import eval_cmd
    ids = ["a", "b"]
    true = {"a": [0.03, 0.0, 0.0], "b": [0.004, 0.0, 0.0]}  # b: |xy| < 1 cm -> not eligible
    rot = {"e0": 0, "e90": 90, "e180": 180}

    def rec(i, cn):
        c = None if cn == "none" else eval_cmd(true[i], rot[cn])
        d = [0.0, 0.0, 0.0] if c is None else list(c)
        p = "plus_x" if c is None else V.dir_xy_bin(c)
        return {"event": "item", "id": i, "cond": cn, "cmd": None if c is None else list(c), "true_cmd": true[i],
                "preds": {"dir_xy": p, "dir_z": "up"}, "targets": {"dir_xy": ["plus_x"], "dir_z": ["down"]},
                "disp": d}
    p = tmp_path / "c1.jsonl"
    _write(p, ids, "c1", rec)
    recs = V.load(str(p), ids, "c1")
    corr, n_it, el, ok = V.per_snapshot(recs, ids, "c1")
    assert corr.tolist() == [1, 1] and n_it.tolist() == [2, 2]
    assert el["e90"].tolist() == [True, False] and V.compliance(el, ok) == 1.0
    # the same records scored as c0 (its none record): plus_x never matches plus_y / minus_x
    p0 = tmp_path / "c0.jsonl"
    _write(p0, ids, "c0", rec)
    corr0, _, el0, ok0 = V.per_snapshot(V.load(str(p0), ids, "c0"), ids, "c0")
    assert V.compliance(el0, ok0) == 0.0 and V.compliance(el0, ok0, rots=("e0",)) == 0.0


def test_load_refuses_missing_or_duplicate_records(tmp_path):
    p = tmp_path / "x.jsonl"
    _write(p, ["a"], "c0", lambda i, cn: {"id": i, "cond": cn})
    with pytest.raises(SystemExit):
        V.load(str(p), ["a", "b"], "c0")
    with pytest.raises(SystemExit):
        V.load(str(p), ["a"], "c1")
    with open(p, "a") as f:
        f.write(json.dumps({"id": "a", "cond": "none"}) + "\n")
    with pytest.raises(SystemExit):
        V.load(str(p), ["a"], "c0")
    assert np.isnan(V.compliance({"e90": np.zeros(1, bool), "e180": np.zeros(1, bool)},
                                 {"e90": np.zeros(1, bool), "e180": np.zeros(1, bool)}))
