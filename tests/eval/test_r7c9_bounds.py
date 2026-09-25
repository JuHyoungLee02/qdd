"""R7 cycle 9 boundary audit (canon §74): every pre-registered numeric threshold decides on the unrounded value, at its
boundary exactly as worded (≥ / ≤ / < / >), without float artefacts (stats.CMP_EPS)."""
from fractions import Fraction as F

import numpy as np
import pytest

from harvest.analysis.replay import judge_e05
from harvest.runtime import calibration as K


def _base(**kw):
    j = {"flip_rate_success": 0.2, "gain_la2": 0.0, "gain_c2pp": 0.0,
         "gain_holm": {"la2": {"reject": False, "lo": -0.1}, "c2pp": {"reject": False, "lo": -0.1}}}
    j.update(kw)
    return j


# ------------------------------------------------------------------------------------------ E0.5
def test_j4_auroc_margin_exactly_003_counts():
    """E §2A.6-4 "AUROC가 0.03 이상 높은 쪽": 0.83 vs 0.80 (8.3/10 vs 8/10) is a margin of exactly 0.03."""
    r = judge_e05(_base(perturb_flip=0.5, auroc={"tv_distance": 0.80, "one_flip": 0.83}))
    assert r["c_flip_default"] == "one_flip"
    r = judge_e05(_base(perturb_flip=0.5, auroc={"tv_distance": 0.80, "one_flip": 0.8299}))
    assert r["c_flip_default"] == "tv_distance"


def test_j9_neutral_bound_exactly_minus_002():
    lay = {"a1_minus_a0_lo": 0.08 - 0.1, "a3_follow_minus_floor_lo": 0.1, "a0_minus_a1_lo": -0.1, "a4_flip": 0.0}
    assert judge_e05(_base(layers={"L": lay}))["name_rule"]["L"] == "neutral"  # 0.08 - 0.1 = -0.020000000000000004


def _synth_one_flip():
    """dir_z answers 'up' only at k = 5 of 10 snapshots: 2 of the 9 successive pairs flip for dir_z, 0 for target ->
    pooled success flip = 2 / 18 = 1/9 (0.1111 when rounded to 4 dp)."""
    from .test_e05_pure import NAMES, OPTS, Q
    eps, ans, truth = [], {}, {}
    for s in range(6):
        eps.append({"cluster": ("P0", s), "kind": "P0", "seed": s, "success": True, "events_t": [],
                    "t": {k: round(0.33 * k, 2) for k in range(10)}})
        for k in range(10):
            vote = {"dir_z": "up" if k == 5 else "down", "target": "o3"}
            v = {q: {"key": vote[q], "name": NAMES[q][vote[q]]} for q in Q}
            ans[("P0", s, k)] = {"vote": vote, "same": [dict(vote)] * 3, "var": {x: v for x in ("A1", "A2", "A3", "A4")},
                                 "rt": {0: [dict(vote), dict(vote)], 1: [dict(vote), dict(vote)]},
                                 "s1": {"dir_z": "down", "target": "o3"}, "opts": OPTS, "names": NAMES}
            truth[("P0", s, k)] = {"dir_z": {"down"}, "target": {"o3"}}
    return eps, ans, truth


def test_e05_judge_input_is_not_rounded():
    """E0.5 judgments read the unrounded statistics (the 4-dp values are for display)."""
    from harvest.eval import e05

    from .test_e05_pure import Q
    eps, ans, truth = _synth_one_flip()
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=200)
    assert r["flip"]["pooled"]["success"]["mean"] == 0.1111  # display
    assert r["judge_input"]["flip_rate_success"] == pytest.approx(1 / 9, abs=1e-15)


def test_gain_holm_lower_bound_not_rounded():
    """A tiny positive lower bound must stay > 0 in the judge (rounding it to 4 dp made it 0.0)."""
    from harvest.eval import e05
    la2 = {("P0", s): [1] + [0] * 99999 for s in range(3)}  # every cluster the same gain 1e-5 -> CI [1e-5, 1e-5]
    h = e05.gain_holm(la2, {c: [0] * 100000 for c in la2}, n=200)
    assert h["la2"]["reject"] and h["la2"]["lo"] > 0


# ------------------------------------------------------------------------------------------ E1
_EV = {"wrong": 40, "auroc_cal": {"mean": 0.9, "ci": [0.85, 0.95]}, "ece_cal_mass": 0.01, "ece_cal_mass_ci": [0.0, 0.02],
       "theta": {"0.8": {"acc": {"mean": 0.77, "ci": [0.72, 0.8]}, "coverage": 0.2}}, "j5": {}}


def test_theta_gate_at_theta_minus_008():
    """E §3.7-1 (iii) "하한 ≥ θ − 0.08": θ 0.8 -> 0.72 (0.8 - 0.08 = 0.7200000000000001 in float)."""
    assert K.judge_question(_EV, 500, (0.8,))["theta_gate"]["0.8"] is True


def _blocks(n_correct, conf=0.75, groups=15, size=100):
    return [{"probs": {"A": conf, "B": 1 - conf}, "truth": {"A"} if i < n_correct else {"B"}, "key": "A"}
            for _ in range(groups) for i in range(size)]


def test_raw_ece_exactly_003_uses_raw(monkeypatch):
    """E §3.6 "원 확률 ECE ≤ 0.03": acc 78/100 at confidence 0.75 is an ECE of exactly 0.03."""
    monkeypatch.setattr(K, "fit_temperature", lambda items: 1.0)
    for nc in (78, 72):
        assert abs(F(nc, 100) - F(3, 4)) == F(3, 100)
        assert K.fit_question(_blocks(nc), _blocks(nc))["use_raw"] is True
    assert K.fit_question(_blocks(79), _blocks(79))["use_raw"] is False


def test_auroc_judged_unrounded():
    """30 wrong / 570 correct, AUROC 12824.5/17100 = 0.749971 < 0.75 (was rounded to 0.75 before '>= 0.75')."""
    items, cid = [], 0
    for score, correct, n in ((0.7, False, 29), (0.8, False, 1), (0.9, True, 427), (0.7, True, 1), (0.6, True, 142)):
        for _ in range(n):
            items.append({"cluster": cid, "probs": {"A": score, "B": 1 - score}, "truth": {"A"} if correct else {"B"},
                          "key": "A", "ambiguous": False})
            cid += 1
    ev = K.evaluate(items, {"T_used": 1.0, "j5": {}}, alphas=(), thetas=(), n_boot=200)
    assert ev["auroc_cal"]["mean"] == 0.75  # display (4 dp)
    assert ev["judge_values"]["auroc"] == pytest.approx(12824.5 / 17100, abs=1e-15)
    assert K.judge_question(ev, 400, ())["auroc_ok"] is False


def test_j5_bounds_exact():
    ev = dict(_EV, theta={}, j5={str(a): {"coverage": {"ci": [float(F(1) - F(str(a)) - F("0.03")), 1.0]},
                                          "singleton_rate": 0.5, "singleton_acc": float(F(1) - F(str(a)))}
                                 for a in (0.05, 0.1, 0.2)})
    assert all(K.judge_question(ev, 400, ())["j5_ok"].values())


# ------------------------------------------------------------------------------------------ M1 near band
def test_near_enters_at_exactly_5cm():
    """M1 :140 / canon §7 "거리 ≤ 5 cm 들어가기 / 6 cm 나가기"."""
    from harvest.predicates import Gripper, Obj, PredicateState
    from harvest.stereo.pipeline import near_update
    q = np.array([1.0, 0.0, 0.0, 0.0])
    a = Obj("a", np.array([0.0, 0.0, 0.05]), q, np.array([0.01, 0.01, 0.01]))
    b = Obj("b", np.array([0.0, 0.05, 0.05]), q, np.array([0.01, 0.01, 0.01]))
    g = Gripper(0.08, 0.0, np.array([0.5, 0.5, 0.5]))
    out = PredicateState().update({"a": a, "b": b}, g, set(), {})
    assert out["near(a,b)"] is True
    assert near_update(False, 0.05) is True and near_update(True, 0.06) is True and near_update(True, 0.0601) is False


def test_ambiguous_band_is_the_history_dependent_part():
    """At exactly 5 cm near is true whatever the history -> not ambiguous; (5, 6] cm depends on it."""
    from harvest.sim.snapshot import ambiguous_predicates
    assert ambiguous_predicates({"a": [0, 0, 0], "b": [0, 0.05, 0]}) == []
    assert ambiguous_predicates({"a": [0, 0, 0], "b": [0, 0.055, 0]}) == ["near(a,b)", "near(b,a)"]
    assert ambiguous_predicates({"a": [0, 0, 0], "b": [0, 0.06, 0]}) != []
