"""R7 cycle 13 D1: the E0.5 FLIP_TH initial value is the split-conformal threshold of the success-run flip scores,
per question (M4 §4.4 FLIP_TH row :287 "성공 실행 flip_score의 1−α 분위(split conformal) … E0.5 재생 자료로 먼저
잡는다 … `question_id@vN`별로 잡는다(J4)"; canon §28 J4 :260 "감시는 `question_id@vN`별로만"; the conformal rank
is the one of M4 §4.4 q̂ row :283 / E §3.5 :330 "⌈(n+1)(1−α)⌉"). The runtime flip_score is per question
(runtime/m4._update_flip), so the score is per question, never the mean over the 5 questions. Canon §79."""
import numpy as np
import pytest

from harvest.eval import e05

from .test_e05_pure import Q, _synth


# ------------------------------------------------------------------------------------------ the conformal rule
def test_n47_alpha001_has_no_finite_threshold():
    # ceil((47 + 1) * 0.99) = ceil(47.52) = 48 > 47 -> no finite threshold; alpha 0.01 needs n >= 1/0.01 - 1 = 99
    r = e05.flip_th_conformal([0.1] * 47, 0.01)
    assert r == {"value": None, "finite": False, "n": 47, "rank": 48, "n_needed": 99}


def test_n99_alpha001_is_the_largest_score():
    s = [i / 100 for i in range(99)]  # 0.00 .. 0.98
    r = e05.flip_th_conformal(s[::-1], 0.01)  # order of the input does not matter
    assert r["rank"] == 99 and r["finite"] is True and r["value"] == 0.98 and r["n_needed"] == 99


def test_rank_not_interpolated_quantile():
    s = list(range(200))  # n 200, alpha 0.05: ceil(201 * 0.95) = ceil(190.95) = 191 -> the 191st smallest = 190
    r = e05.flip_th_conformal(s, 0.05)
    assert r["rank"] == 191 and r["value"] == 190
    assert float(np.quantile(s, 0.95)) == pytest.approx(189.05)  # the old np.quantile value differs
    assert r["n_needed"] == 19  # 1/0.05 - 1


@pytest.mark.parametrize("alpha,n_needed", [(0.001, 999), (0.01, 99), (0.05, 19)])
def test_n_needed_is_the_first_n_with_a_finite_rank(alpha, n_needed):
    assert e05.flip_th_conformal([0.0] * n_needed, alpha)["finite"] is True
    assert e05.flip_th_conformal([0.0] * (n_needed - 1), alpha)["finite"] is False
    assert e05.flip_th_conformal([0.0] * (n_needed - 1), alpha)["n_needed"] == n_needed


def test_empty_scores():
    assert e05.flip_th_conformal([], 0.01) == {"value": None, "finite": False, "n": 0, "rank": 1, "n_needed": 99}


# ------------------------------------------------------------------------------------------ analyze(): per question
def test_flip_th_is_per_question_on_the_per_question_score():
    """dir_z alternates down / up at every snapshot, target never changes. Each step's 3 votes are then (x, y, x) and
    the previous step's (y, x, y): per-question TV 1/3 and one-answer flip 1.0 for dir_z at every step, 0 for target.
    17 episodes x 6 scored steps (k 4..9; k 3 has no previous step) = 102 success steps per question; alpha 0.01:
    rank ceil(103 * 0.99) = 102 = the largest score."""
    eps, ans, truth = _synth(n_ep=17, flip=True)
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=50)
    ini = r["c_flip"]["flip_th_initial"]
    assert ini["alpha"] == 0.01 and ini["key"] == "q0.99"
    pq = ini["per_question"]
    assert set(pq) == set(Q)
    assert pq["dir_z"]["n"] == 102 and pq["dir_z"]["rank"] == 102 and pq["dir_z"]["finite"] is True
    assert pq["dir_z"]["tv_distance"] == pytest.approx(1 / 3)  # the question-mean score would be 1/6
    assert pq["dir_z"]["one_flip"] == pytest.approx(1.0)  # the question-mean score would be 0.5
    assert pq["target"]["tv_distance"] == 0.0 and pq["target"]["one_flip"] == 0.0
    c = r["c_flip"]["flip_th_candidates"]
    assert set(c) == {"q0.99", "q0.999", "q0.95"}
    assert c["q0.99"] == pq
    # alpha 0.001 needs n >= 999: no finite threshold from 102 steps
    assert c["q0.999"]["dir_z"]["tv_distance"] is None and c["q0.999"]["dir_z"]["n_needed"] == 999


def test_small_sample_reports_no_threshold_and_the_n_needed():
    eps, ans, truth = _synth(n_ep=8, flip=True)  # 48 success steps per question
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=50)
    d = r["c_flip"]["flip_th_initial"]["per_question"]["dir_z"]
    assert d["n"] == 48 and d["rank"] == 49 and d["finite"] is False
    assert d["tv_distance"] is None and d["one_flip"] is None and d["n_needed"] == 99


def test_perturbed_and_failed_steps_are_not_in_the_success_scores():
    e0, a0, t0 = _synth(n_ep=2, flip=False)  # success P0: all scores 0
    e1, a1, t1 = _synth(n_ep=2, flip=True, kind="P1")  # perturbed: dir_z flips at every step
    r = e05.analyze(e0 + e1, {**a0, **a1}, {**t0, **t1}, questions=Q, d_p95=0.307, n_boot=50)
    d = r["c_flip"]["flip_th_candidates"]["q0.95"]["dir_z"]  # alpha 0.05 needs n >= 19 -> 12 steps: none
    assert d["n"] == 12 and d["finite"] is False
