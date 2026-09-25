"""R6 calib: per-question temperature (E §3.6), J5 split conformal (canon §31, E §3.5/§3.7-8), runtime file."""
import json
import math

import numpy as np
import pytest

from harvest.runtime import calibration as K


def _items(n=400, conf=0.9, acc=0.6, seed=0):
    """3-option items whose top prob is `conf` but right only `acc` of the time (overconfident)."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        top = "a"
        y = "a" if rng.random() < acc else ("b" if rng.random() < 0.5 else "c")
        out.append({"cluster": ("P0", i // 10), "probs": {"a": conf, "b": (1 - conf) / 2, "c": (1 - conf) / 2},
                    "truth": {y}, "key": top})
    return out


def test_apply_temperature_one_is_identity_and_high_t_flattens():
    p = {"a": 0.7, "b": 0.2, "c": 0.1}
    assert K.apply_temperature(p, 1.0) == pytest.approx(p)
    q = K.apply_temperature(p, 5.0)
    assert q["a"] < 0.7 and sum(q.values()) == pytest.approx(1.0)


def test_fit_temperature_cools_an_overconfident_model():
    T = K.fit_temperature(_items())
    assert T > 1.0
    # after scaling, mean top probability is close to the accuracy
    items = _items()
    top = np.mean([K.apply_temperature(x["probs"], T)["a"] for x in items])
    acc = np.mean([("a" in x["truth"]) for x in items])
    assert abs(top - acc) < 0.03


def test_conformal_qhat_is_the_finite_sample_quantile():
    s = [i / 100 for i in range(1, 100)]  # n = 99
    q = K.conformal_qhat(s, 0.1)
    assert q == pytest.approx(s[math.ceil(100 * 0.9) - 1])
    assert K.conformal_qhat([0.1, 0.2], 0.01) == float("inf")  # too few points for 1 - alpha: everything is in


def test_prediction_set():
    p = {"a": 0.8, "b": 0.15, "c": 0.05}
    assert K.pred_set(p, 0.3) == {"a"}
    assert K.pred_set(p, 0.9) == {"a", "b"}


def test_fit_question_and_file_roundtrip(tmp_path):
    fit_t, fit_c = _items(seed=1), _items(seed=2)
    qc = K.fit_question(fit_t, fit_c, alphas=(0.1, 0.2))
    assert qc["T"] > 1 and set(qc["j5"]) == {"0.1", "0.2"} and qc["n_fit_T"] == 400 and qc["n_fit_j5"] == 400
    cal = {"format": K.FORMAT, "model": {"fingerprint": "abc"}, "question_ids": {"dir_z": "h1@v1"},
           "questions": {"dir_z": {**qc, "j5_ok": {"0.1": True, "0.2": False}}}}
    p = tmp_path / "calibration.json"
    p.write_text(json.dumps(cal))
    c = K.Calibration.load(str(p), fingerprint="abc", question_ids={"dir_z": "h1@v7"})  # @vN ordinal ignored
    got = c.apply("dir_z", {"a": 0.9, "b": 0.05, "c": 0.05})
    assert got["a"] < 0.9
    assert c.j5_on("dir_z", 0.1) and not c.j5_on("dir_z", 0.2) and not c.j5_on("target", 0.1)
    assert c.set_for("dir_z", got, 0.1) <= {"a", "b", "c"}
    with pytest.raises(ValueError, match="fingerprint"):
        K.Calibration.load(str(p), fingerprint="zzz", question_ids={"dir_z": "h1@v1"})
    with pytest.raises(ValueError, match="question_id"):
        K.Calibration.load(str(p), fingerprint="abc", question_ids={"dir_z": "h2@v1"})


def test_evaluate_reports_the_e1_quantities():
    items = _items(seed=3)
    qc = K.fit_question(_items(seed=1), _items(seed=2), alphas=(0.1,))
    ev = K.evaluate(items, qc, alphas=(0.1,), n_boot=200)
    for k in ("acc", "ece_raw", "ece_cal", "ece_cal_mass", "auroc_cal", "theta", "j5"):
        assert k in ev, k
    j = ev["j5"]["0.1"]
    assert 0 <= j["coverage"]["mean"] <= 1 and j["set_size_mean"] >= 1
    assert "singleton_rate" in j and "ne_in_set_rate" in j and "singleton_acc" in j and "empty_rate" in j
    assert ev["ece_cal"] < ev["ece_raw"]


def test_judge_question_follows_e1_rules():
    ev = {"ece_cal_mass": 0.03, "ece_cal_mass_ci": [0.02, 0.05], "auroc_cal": {"mean": 0.8, "ci": [0.72, 0.86]},
          "wrong": 40, "theta": {"0.8": {"acc": {"mean": 0.85, "ci": [0.8, 0.9]}, "coverage": 0.4}},
          "j5": {"0.1": {"coverage": {"mean": 0.9, "ci": [0.88, 0.92]}, "singleton_rate": 0.6,
                         "singleton_acc": 0.93}}}
    j = K.judge_question(ev, n_fit_j5=400, thetas=(0.8,))
    assert j["theta_gate"]["0.8"] is True and j["j5_ok"]["0.1"] is True and j["j5_guarantee"] is True
    ev["j5"]["0.1"]["singleton_rate"] = 0.3
    assert K.judge_question(ev, n_fit_j5=100, thetas=(0.8,))["j5_ok"]["0.1"] is False
    ev["wrong"] = 10
    assert K.judge_question(ev, n_fit_j5=400, thetas=(0.8,))["auroc_judgeable"] is False
