"""tools/marr_real/verdict.py (prereg_marr §5) on synthetic predictions."""
import json
import math
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "marr_real", "verdict.py")
RUNS = ("c0_s1", "a_s1", "c0_s2", "a_s2")
QS = ("dir_xy", "dir_z", "mag_coarse")


def _key(i):
    return f"{'RB1' if i % 2 else 'RB2'}_ep{i}_k0"


def _run(tmp, acc, runtime="yes", drop_label=False, n_val=40):
    """40 snapshots x 3 questions, snapshots 0-19 transitions; acc[run] = (steady fraction, transition fraction)."""
    flags = {_key(i): {"transition": i < 20, "per_q": {q: i < 20 for q in QS}} for i in range(40)}
    tp = tmp / "trans.json"
    tp.write_text(json.dumps({"meta": {}, "flags": flags}))
    lab = [{"key": _key(i), "trace255": [[1, 2]] if i % 4 == 0 else None} for i in range(0, 40, 2)]
    if drop_label:
        lab = lab[1:]
    lp_ = tmp / "RB2.tracept.jsonl"
    lp_.write_text("".join(json.dumps(r) + "\n" for r in lab))
    pred = []
    for c in RUNS:
        recs = []
        for i in range(40):
            frac = acc[c][1] if i < 20 else acc[c][0]
            for j, q in enumerate(QS):
                ok = (i * 3 + j) % 20 < round(frac * 20)
                lp = {"a": math.log(0.7), "b": math.log(0.3)} if ok else {"a": math.log(0.3), "b": math.log(0.7)}
                recs.append({"event": "item", "key": _key(i), "question": q, "target": ["a"],
                             "pred": "a" if ok else "b", "correct": ok, "lp": lp})
        p = tmp / f"{c}.jsonl"
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))
        pred.append(f"{c}={p}")
    out = tmp / "v.json"
    r = subprocess.run([sys.executable, TOOL, "--pred", *pred, "--trans", str(tp), "--labels", str(lp_),
                        "--runtime-identical", runtime, "--out", str(out), "--n-val", str(n_val)],
                       capture_output=True, text=True)
    return r, (json.loads(out.read_text()) if r.returncode == 0 else None)


def test_adopted_and_strata(tmp_path):
    acc = {"c0_s1": (0.70, 0.60), "a_s1": (0.80, 0.70), "c0_s2": (0.70, 0.60), "a_s2": (0.80, 0.70)}
    r, v = _run(tmp_path, acc)
    assert r.returncode == 0, r.stderr
    assert v["verdict"]["adopt"] and v["verdict"]["pooled_overall"] > 0.09 and v["verdict"]["lower_95"] > 0
    assert v["strata"]["RB2"]["n_snap"] == 20 and v["strata"]["RB2_labelled"]["n_snap"] == 10
    assert v["strata"]["RB1"]["n_snap"] == 20 and v["rule"]["min_gain"] == 0.02


def test_runtime_change_blocks(tmp_path):
    acc = {"c0_s1": (0.70, 0.60), "a_s1": (0.80, 0.70), "c0_s2": (0.70, 0.60), "a_s2": (0.80, 0.70)}
    _, v = _run(tmp_path, acc, runtime="no")
    assert v["verdict"]["c_point"] and not v["verdict"]["adopt"]


def test_below_gain_and_transition_drop(tmp_path):
    acc = {"c0_s1": (0.70, 0.60), "a_s1": (0.70, 0.65), "c0_s2": (0.70, 0.60), "a_s2": (0.70, 0.60)}
    _, v = _run(tmp_path, acc)
    assert v["verdict"]["pooled_overall"] < 0.02 and not v["verdict"]["adopt"]
    acc = {"c0_s1": (0.60, 0.70), "a_s1": (0.75, 0.65), "c0_s2": (0.60, 0.70), "a_s2": (0.75, 0.65)}
    _, v = _run(tmp_path, acc)
    assert v["verdict"]["c_point"] and not v["verdict"]["c_transition"] and not v["verdict"]["adopt"]


def test_input_checks(tmp_path):
    acc = {c: (0.7, 0.6) for c in RUNS}
    r, _ = _run(tmp_path, acc, n_val=1799)
    assert r.returncode != 0 and "snapshots" in r.stderr
    r, _ = _run(tmp_path, acc, drop_label=True)
    assert r.returncode != 0 and "without a label record" in r.stderr
