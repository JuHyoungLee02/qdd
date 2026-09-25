"""R7 cycle 8 fixes: the evaluation code follows the pre-registration (E-first §1.7, §1.8, §2A.6-2, §3.10, §4.12;
canon §28, §73)."""
import numpy as np
import pytest

from harvest.analysis.replay import judge_e05
from harvest.analysis.stats import cluster_bootstrap_ci, holm_ci
from harvest.eval import closed, e05

# R7 cycle-8 reviewer counter-example (j2_holm.py, rng seed 3, trial 186): LA-2 - newest per episode, 30 episodes.
# 95% cluster CI lower bound > 0 (0.0099) but the Holm first-step (97.5%) lower bound is 0.0.
_LA2 = [[1, -1, 0, 0, 0, 0, 1, 0, 0, 1], [0, 1, 0, 0, 0, 1, 0, 0, -1, 1], [-1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 1, 1, 0, 1, 0, 1, 0], [-1, 0, 0, 0, 0, 0, 0, -1, 0, -1], [0, 0, -1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, -1, 0, 1, 0, 1], [0, 0, 0, 1, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 1, -1, 0, 0, 0, 0],
        [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-1, 0, 0, -1, 0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 1, 0, 1, 1],
        [0, -1, 0, -1, 0, 0, 0, 0, 1, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, -1, 1, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 0, 0, -1, 0, 1, 0], [0, 0, 0, 0, 0, 1, 1, 0, 0, 0], [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, -1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, -1, 0, 0, 0, -1, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 0], [0, 0, 1, 0, 0, 0, 0, -1, 0, 0],
        [0, 0, 1, 1, 0, 0, 0, 0, -1, 0], [0, 0, 0, 0, 0, 0, -1, -1, 0, 0], [0, 1, 1, 1, 0, 0, 0, 0, 0, -1],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 1, 0, 0, 1, 0, 1], [0, 0, 0, 0, 1, 0, 0, 1, -1, 0]]


# ------------------------------------------------------------------------------------------ D1: judgment 2 Holm
def test_judgment2_uses_holm_over_la2_and_c2pp():
    """E §1.7 (:131) "한 판정에 여러 조건을 걸면 Holm", judgment 2 = "LA-2 또는 C2''" (:257): with the 95% lower
    bound > 0 but the Holm first-step (1 - 0.05/2) bound not, judgment 2 does not hold."""
    la2 = {("P0", s): v for s, v in enumerate(_LA2)}
    c2pp = {c: [0] * len(v) for c, v in la2.items()}
    assert e05.mean_ci(la2)["ci"][0] > 0  # the uncorrected bound the old code used
    h = e05.gain_holm(la2, c2pp)
    assert set(h) == {"la2", "c2pp"}
    assert h["la2"]["reject"] is False and h["c2pp"]["reject"] is False
    assert h["la2"]["level"] == pytest.approx(0.975)
    j = {"flip_rate_success": 0.2, "gain_la2": 0.0633, "gain_c2pp": 0.0, "gain_holm": h}
    # not judgment 2; judgment 3 needs the point gain < +2 pp (E :258), so the case is outside 1-3 -> undecided
    assert judge_e05(j)["claim"] == "undecided"


def test_judgment2_holds_when_holm_rejects_with_a_positive_gain():
    la2 = {("P0", s): [1] * 5 + [0] * 5 for s in range(30)}
    c2pp = {c: [0] * 10 for c in la2}
    h = e05.gain_holm(la2, c2pp, n=2000)
    assert h["la2"]["reject"] is True and h["la2"]["lo"] > 0 and h["c2pp"]["reject"] is False
    assert judge_e05({"flip_rate_success": 0.2, "gain_la2": 0.5, "gain_c2pp": 0.0, "gain_holm": h})["claim"] == "keep_a"
    # a significant NEGATIVE gain is a Holm rejection but not judgment 2
    neg = e05.gain_holm({c: [-1] * 5 + [0] * 5 for c in la2}, c2pp, n=2000)
    assert neg["la2"]["reject"] is True and neg["la2"]["hi"] < 0
    assert judge_e05({"flip_rate_success": 0.2, "gain_la2": 0.03, "gain_c2pp": 0.0, "gain_holm": neg})["claim"] \
        != "keep_a"


def test_analyze_reports_the_judgment2_holm_per_hypothesis():
    from .test_e05_pure import Q, _synth
    eps, ans, truth = _synth(flip=True)
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=200)
    h = r["judgments"]["j2_gain_holm"]
    assert set(h["tests"]) == {"la2", "c2pp"} and h["alpha"] == 0.05
    for k in ("la2", "c2pp"):
        assert set(h["tests"][k]) == {"reject", "lo", "hi", "level"}
    assert r["judge_input"]["gain_holm"] == h["tests"]


# ------------------------------------------------------------------------------------------ D2: ambiguous items
def _items():
    """20 clean items (p 0.7, 14 right) + 10 ambiguous items (p 0.9, all wrong)."""
    it = []
    for i in range(20):
        it.append({"cluster": ("P0", i % 5), "probs": {"a": 0.7, "b": 0.3}, "truth": {"a"} if i < 14 else {"b"},
                   "key": "a", "ambiguous": False})
    for i in range(10):
        it.append({"cluster": ("P0", i % 5), "probs": {"a": 0.9, "b": 0.1}, "truth": {"b"}, "key": "a",
                   "ambiguous": True})
    return it


def test_judged_ece_excludes_ambiguous_items_and_reports_them_apart():
    """E §3.10 (:359): "`ambiguous` 항목은 본 ECE에서 빼고 따로 보고"."""
    from harvest.runtime import calibration as K
    qc = {"T_used": 1.0, "j5": {"0.1": {"qhat": 0.5}}}
    ev = K.evaluate(_items(), qc, alphas=(0.1,), n_boot=50)
    clean = round(K.ece_mass([0.7] * 20, [1] * 14 + [0] * 6), 5)
    assert ev["ece_cal_mass"] == clean != round(K.ece_mass([0.7] * 20 + [0.9] * 10, [1] * 14 + [0] * 16), 5)
    assert ev["ambiguous"]["n"] == 10
    assert ev["ambiguous"]["ece_cal_mass"] == pytest.approx(0.9)
    assert ev["n"] == 30  # other metrics keep every item (the pre-registration excludes them from the ECE only)
    assert ev["n_ece"] == 20


def test_raw_probability_rule_ece_excludes_ambiguous_items():
    from harvest.runtime import calibration as K
    it = _items()
    qc = K.fit_question(it, it, alphas=(0.1,))
    assert qc["fit_raw_ece"] == round(K.ece_mass([0.7] * 20, [1] * 14 + [0] * 6), 5)
    assert qc["n_fit_ambiguous"] == 10


def test_items_carry_the_snapshot_ambiguous_flag():
    from harvest.eval import calib
    eps = [{"dir": "d", "seed": 0, "kind": "P0", "lines": [{"k": 0, "ambiguous": True}, {"k": 1}]}]
    done = {("d", 0, k, "A0#0"): {"answers": {"target": {"key": "o3", "probs": {"o3": 0.8, "o5": 0.2}}}}
            for k in (0, 1)}
    truth = {("P0", 0, k): {"target": {"o3"}} for k in (0, 1)}
    out = calib.items_from(eps, done, truth, ("target",))
    assert [x["ambiguous"] for x in out["target"]] == [True, False]


# ------------------------------------------------------------------------------------------ D3: canary drift rule
def test_canary_drift_is_lower_bound_above_floor_without_the_2x_condition():
    """Canon §28 (:264) / E §1.8: drift = mismatch significantly above the day's floor (lower > 0, Holm); no
    'mismatch > 2 x floor' condition (reviewer canary_rule.py: floor 0.10, mismatch 0.18)."""
    from harvest.canary import canary_compare
    base = {f"s{i}|dir_xy": ["a"] * 3 for i in range(60)}
    today = {k: (["b", "a", "a", "a", "a"] if i % 10 < 9 else ["a"] * 5) for i, k in enumerate(base)}
    r = canary_compare(base, today, floor=0.10)
    assert r["mismatch"] == pytest.approx(0.18)
    assert r["drift_suspect"] is True


def test_canary_resamples_episodes_and_holms_over_questions():
    from harvest.canary import canary_compare, episode_of_key
    assert episode_of_key("P0_ep2_k15|dir_xy") == "P0_ep2"
    qs = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")
    base, today = {}, {}
    rng = np.random.default_rng(0)
    for e in range(3):
        for k in range(4):
            for q in qs:
                key = f"P0_ep{e}_k{k}|{q}"
                base[key] = ["a", "a"]
                today[key] = ["b" if rng.random() < (0.5 if q == "dir_xy" else 0.0) else "a" for _ in range(2)]
    r = canary_compare(base, today, floor=0.05, n_boot=2000)
    assert r["n_clusters"] == 3 and "episode" in r["boot_unit"]
    pq = r["per_question"]
    assert set(pq) == set(qs)
    by_q = {q: {} for q in qs}
    for key, ans in today.items():
        snap, q = key.rsplit("|", 1)
        by_q[q].setdefault(episode_of_key(snap), []).extend(float(a != "a") for a in ans)
    ref = holm_ci(lambda q, L: cluster_bootstrap_ci(by_q[q], lambda xs: sum(xs) / len(xs) - 0.05, n=2000,
                                                    level=L), sorted(qs))
    for q in qs:
        assert pq[q]["reject"] == ref[q]["reject"] and pq[q]["lo"] == pytest.approx(ref[q]["lo"])
        assert pq[q]["level"] == pytest.approx(ref[q]["level"])
    assert r["drift_suspect"] == any(v["reject"] and v["lo"] > 0 for v in ref.values())


# ------------------------------------------------------------------------------------------ E §1.7 hash line
def test_run_meta_records_the_prereg_hashes_and_check():
    """E §1.7 (:133): the judgment sections' SHA-256 and time go into the run record (docs/stage3/prereg.json)."""
    import json
    import os

    from harvest.eval import common as C
    saved = json.load(open(os.path.join(C.REPO, "docs", "stage3", "prereg.json"), encoding="utf-8"))
    m = C.run_meta("x", {"kind": "mock", "path": None, "spec": "mock"})
    p = m["prereg"]
    assert p["written_utc"] == saved["written_utc"] and p["hashes"] == saved["hashes"]
    assert p["check"] == "OK"
    assert list(m).index("prereg") < list(m).index("model")  # at the head of the record


# ------------------------------------------------------------------------------------------ N8: H argument
def test_closed_has_an_m4_horizon_argument_default_3():
    from dataclasses import asdict

    from harvest.runtime.m4 import M4Params
    assert closed._args(["--model", "m", "--out", "o"]).m4_h == 3
    assert closed._args(["--model", "m", "--out", "o", "--m4-h", "1"]).m4_h == 1
    assert closed.m4_config("C5", 3) == asdict(M4Params())  # default unchanged
    assert closed.m4_config("C3", 3) == {**asdict(M4Params()), "feedback_b": False}
    assert closed.m4_config("C5", 1)["H"] == 1
    with pytest.raises(ValueError):
        closed.m4_config("C5", 0)
