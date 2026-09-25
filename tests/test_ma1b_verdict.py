"""tools/ma1/ma1b_verdict.py (prereg_ma1b §5) on synthetic predictions."""
import json
import math
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "ma1", "ma1b_verdict.py")
RUNS = ("none_s1", "a3d_s1", "none_s2", "a3d_s2")
QS = ("dir_xy", "dir_z", "mag_coarse")


def _run(tmp, acc):
    """40 snapshots x 3 questions, snapshots 0-19 transitions; acc[run] = (steady fraction, transition fraction)."""
    flags = {f"{'RB1' if i % 2 else 'RB2'}_ep{i}_k0": {"transition": i < 20, "per_q": {q: i < 20 for q in QS}}
             for i in range(40)}
    tp = tmp / "trans.json"
    tp.write_text(json.dumps({"meta": {}, "flags": flags}))
    pred = []
    for c in RUNS:
        recs = []
        for i in range(40):
            frac = acc[c][1] if i < 20 else acc[c][0]
            for j, q in enumerate(QS):
                ok = (i * 3 + j) % 20 < round(frac * 20)
                lp = {"a": math.log(0.7), "b": math.log(0.3)} if ok else {"a": math.log(0.3), "b": math.log(0.7)}
                recs.append({"event": "item", "key": f"{'RB1' if i % 2 else 'RB2'}_ep{i}_k0", "question": q,
                             "target": ["a"], "pred": "a" if ok else "b", "correct": ok, "lp": lp})
        p = tmp / f"{c}.jsonl"
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))
        pred.append(f"{c}={p}")
    out = tmp / "v.json"
    r = subprocess.run([sys.executable, TOOL, "--pred", *pred, "--trans", str(tp), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(out.read_text())


def test_adopted(tmp_path):
    acc = {"none_s1": (0.70, 0.60), "a3d_s1": (0.80, 0.70), "none_s2": (0.70, 0.60), "a3d_s2": (0.80, 0.70)}
    v = _run(tmp_path, acc)
    assert v["verdict"]["adopt"] and v["verdict"]["pooled_overall"] > 0.09 and v["verdict"]["lower_95"] > 0
    assert set(v["per_source_pooled"]) == {"RB1", "RB2"}
    assert "pooled_effect_nll" in v and v["rule"]["min_gain"] == 0.02


def test_below_gain_not_adopted(tmp_path):
    acc = {"none_s1": (0.70, 0.60), "a3d_s1": (0.70, 0.65), "none_s2": (0.70, 0.60), "a3d_s2": (0.70, 0.60)}
    v = _run(tmp_path, acc)
    assert v["verdict"]["pooled_overall"] < 0.02 and not v["verdict"]["adopt"]


def test_transition_drop_blocks(tmp_path):
    acc = {"none_s1": (0.60, 0.70), "a3d_s1": (0.75, 0.65), "none_s2": (0.60, 0.70), "a3d_s2": (0.75, 0.65)}
    v = _run(tmp_path, acc)
    assert v["verdict"]["c_point"] and not v["verdict"]["c_transition"] and not v["verdict"]["adopt"]
