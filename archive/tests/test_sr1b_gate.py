"""E-SR1b (prereg_sr1b): the reproduction gate (sr1b_eval w = 1 on E-MA2 C0 == E-SR0 evaluation) and the training-run
gate (data count, finite loss, validation not rising, wall time, relabel event); also sr1b_eval's output naming."""
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G = _load("sr1b_gate", ("tools", "sr1b", "sr1b_gate.py"))
TV = _load("t_sr1b_verdict", ("tests", "test_sr1b_verdict.py"))


def _w(path, recs):
    with open(path, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    return str(path)


def _ma2(snaps, wrong=0):
    out = []
    for k, s in enumerate(snaps):
        p = dict(s["preds"])
        if k < wrong:
            p["dir_xy"] = "minus_y"
        out.append({"event": "item", "id": s["id"], "cond": "none", "preds": p, "targets": s["targets"]})
    return out


def test_repro_gate(tmp_path):
    a = [TV.snap(i, True) for i in range(5)]
    b = [TV.snap(i, True) for i in range(5)]
    r = G.gate_repro(_w(tmp_path / "a", a), _w(tmp_path / "b", b), _w(tmp_path / "m", _ma2(a)))
    assert r["pass"] and r["disp_diff_max_m"] == 0 and r["a_xy_new"] == r["a_xy_sr0"] and r["acc_new"] == 1.0
    b2 = [TV.snap(i, i >= 1) for i in range(5)]  # one snapshot's chunks differ
    assert not G.gate_repro(_w(tmp_path / "a", a), _w(tmp_path / "b2", b2), _w(tmp_path / "m", _ma2(a)))["pass"]
    assert not G.gate_repro(_w(tmp_path / "a", a), _w(tmp_path / "b", b), _w(tmp_path / "m2", _ma2(a, 1)))["pass"]
    with pytest.raises(SystemExit):
        G.gate_repro(_w(tmp_path / "a", a), _w(tmp_path / "b3", b[:3]), _w(tmp_path / "m", _ma2(a)))


def _log(tmp_path, n_train=151000, n_val=870, total=1000, dec=(5.0, 0.4, 0.3), nan=False, elapsed=3000):
    recs = [{"event": "config", "n_train": n_train, "n_val": n_val, "total_steps": total, "args": {"eval_every": 500},
             "prompt_config": {"sha": "x", "sr1b": "sr1b@v1", "sr1b_drop": 0.3, "sr1b_relabel": True}},
            {"event": "eval", "step": 0, "dec": dec[0]}]
    for s in range(1, total + 1):
        recs.append({"event": "train", "step": s, "total": float("nan") if nan and s == 7 else 1.0,
                     "elapsed_s": elapsed * s / total})
        if s % 500 == 0:
            recs.append({"event": "eval", "step": s, "dec": dec[s // 500]})
    return _w(tmp_path / "log.jsonl", recs)


def test_train_gate(tmp_path):
    out = _w(tmp_path / "o.out", [{"event": "sr1b_relabel", "n": 151870, "missing": 0}])
    assert G.gate_train(_log(tmp_path), out, relabel=True)["pass"]
    assert not G.gate_train(_log(tmp_path, n_val=869), out, relabel=False)["pass"]
    assert not G.gate_train(_log(tmp_path, nan=True), out, relabel=False)["pass"]
    assert not G.gate_train(_log(tmp_path, dec=(5.0, 6.0, 0.3)), out, relabel=False)["pass"]
    assert not G.gate_train(_log(tmp_path, elapsed=90 * 60 + 1), out, relabel=False)["pass"]
    bad = _w(tmp_path / "o2.out", [{"event": "sr1b_relabel", "n": 151870, "missing": 3}])
    assert not G.gate_train(_log(tmp_path), bad, relabel=True)["pass"]
    assert not G.gate_train(_log(tmp_path), _w(tmp_path / "o3.out", []), relabel=True)["pass"]
    assert G.gate_train(_log(tmp_path, n_train=10, n_val=5), out, relabel=False, n_rows=15)["pass"]


def test_eval_out_path():
    E = _load("sr1b_eval", ("tools", "sr1b", "sr1b_eval.py"))
    assert E.out_path("/x/A_s0", 1.0) == "/x/A_s0_w1.jsonl" and E.out_path("p", 1.5) == "p_w1.5.jsonl"
