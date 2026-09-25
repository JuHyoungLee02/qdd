"""tools/ma1/ma1_verdict.py (prereg_ma1 §6) on synthetic predictions."""
import json
import math
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "ma1", "ma1_verdict.py")
CELLS = ("none+none", "A+none", "none+O", "A+O")
QS = ("dir_xy", "dir_z", "mag_coarse")


def _flags(tmp):
    flags = {f"{'RB1' if i % 2 else 'RB2'}_ep{i}_k0": {"transition": i < 20, "per_q": {q: i < 20 for q in QS}}
             for i in range(40)}
    tp = tmp / "trans.json"
    tp.write_text(json.dumps({"meta": {}, "flags": flags}))
    return tp


def _pred(tmp, name, frac_steady, frac_trans):
    """40 snapshots x 3 questions; snapshots 0-19 are transitions."""
    recs = []
    for i in range(40):
        frac = frac_trans if i < 20 else frac_steady
        for j, q in enumerate(QS):
            ok = (i * 3 + j) % 20 < round(frac * 20)
            lp = {"a": math.log(0.7), "b": math.log(0.3)} if ok else {"a": math.log(0.3), "b": math.log(0.7)}
            recs.append({"event": "item", "key": f"{'RB1' if i % 2 else 'RB2'}_ep{i}_k0", "question": q,
                         "target": ["a"], "pred": "a" if ok else "b", "correct": ok, "lp": lp})
    p = tmp / f"{name}.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return p


def _lat(tmp, p95):
    p = tmp / "lat.json"
    p.write_text(json.dumps({"formats": {c: {"full_p95": p95[c]} for c in CELLS}}))
    return p


def _run(tmp, acc, lat, acc1=None, noov=None):
    tp = _flags(tmp)
    args = [sys.executable, TOOL, "--trans", str(tp), "--lat", str(_lat(tmp, lat)), "--out", str(tmp / "v.json"),
            "--pred", *[f"{c}={_pred(tmp, c + '_s0', *acc[c])}" for c in CELLS]]
    if acc1:
        args += ["--pred1", *[f"{c}={_pred(tmp, c + '_s1', *acc1[c])}" for c in CELLS]]
    if noov:
        args += ["--pred-nooverlay", *[f"{c}={_pred(tmp, c + '_nov', *noov[c])}" for c in noov]]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads((tmp / "v.json").read_text())


BASE_LAT = {"none+none": 0.10, "A+none": 0.10, "none+O": 0.105, "A+O": 0.105}


def test_a_adopted_o_rejected_on_seed0(tmp_path):
    acc = {"none+none": (0.70, 0.60), "A+none": (0.80, 0.70), "none+O": (0.70, 0.60), "A+O": (0.80, 0.70)}
    v = _run(tmp_path, acc, BASE_LAT)
    a, o = v["seed0"]["A"], v["seed0"]["O"]
    assert a["pass"] and a["overall_main_effect"] > 0.09
    assert not o["pass"] and abs(o["overall_main_effect"]) < 1e-12
    assert v["seed1_needed"] == ["A"]
    assert v["final"] is None  # seed 1 not given yet
    assert "RB1" in v["cells"]["none+none"]["per_source"] and "RB2" in v["cells"]["none+none"]["per_source"]
    assert set(v["bootstrap_acc_95"]["all"]) == {"A", "O", "AxO"}


def test_latency_rule_blocks_o(tmp_path):
    acc = {"none+none": (0.70, 0.60), "A+none": (0.70, 0.60), "none+O": (0.80, 0.70), "A+O": (0.80, 0.70)}
    lat = {**BASE_LAT, "none+O": 0.111}
    v = _run(tmp_path, acc, lat)
    assert v["seed0"]["O"]["c1_gain"] and v["seed0"]["O"]["c2_transition"]
    assert not v["seed0"]["O"]["c3_latency"] and not v["seed0"]["O"]["pass"]
    assert v["seed0"]["O"]["p95_increase"] > 0.10


def test_transition_rule(tmp_path):
    # overall +0.025 but the transition stratum drops 0.05 -> not adopted
    acc = {"none+none": (0.60, 0.70), "A+none": (0.70, 0.65), "none+O": (0.60, 0.70), "A+O": (0.70, 0.65)}
    v = _run(tmp_path, acc, BASE_LAT)
    assert v["seed0"]["A"]["overall_main_effect"] >= 0.02
    assert not v["seed0"]["A"]["c2_transition"] and not v["seed0"]["A"]["pass"]


def test_two_seed_mean_decides(tmp_path):
    acc = {"none+none": (0.70, 0.60), "A+none": (0.75, 0.65), "none+O": (0.70, 0.60), "A+O": (0.75, 0.65)}
    acc1 = {"none+none": (0.70, 0.60), "A+none": (0.65, 0.55), "none+O": (0.70, 0.60), "A+O": (0.65, 0.55)}
    v = _run(tmp_path, acc, BASE_LAT, acc1=acc1)
    assert v["seed0"]["A"]["pass"]
    f = v["final"]["A"]
    assert abs(f["overall_main_effect_2seed"] - 0.5 * (v["seed0"]["A"]["overall_main_effect"]
                                                        + v["seed1"]["A"]["overall_main_effect"])) < 1e-12
    assert not f["adopt"]  # seed 1 reverses the gain: 2-seed mean < 0.02
    assert v["final"]["O"]["adopt"] is False and v["final"]["O"]["reason"] == "seed0 rule not passed"
    assert v["vla_overlay"].startswith("drop")


def test_overlay_dependency_warning(tmp_path):
    acc = {"none+none": (0.70, 0.60), "A+none": (0.70, 0.60), "none+O": (0.80, 0.70), "A+O": (0.80, 0.70)}
    noov = {"none+O": (0.70, 0.60), "A+O": (0.78, 0.68)}
    v = _run(tmp_path, acc, BASE_LAT, noov=noov)
    d = v["overlay_dependency"]
    assert d["none+O"]["drop"] > 0.05 and d["none+O"]["warn"] and not d["A+O"]["warn"]
