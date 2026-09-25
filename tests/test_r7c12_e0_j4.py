"""R7 cycle 12 N7: E0 judgment 4 (E §2.7-4 :197, §2.6 :183) -- the offline replay of recorded latencies through
the H = 1 early-ask schedule gives votes per step; the judgment reads their MEDIAN (>= 2 at T_c 0.33, lead_max
1.5 s), and canon §75 (1) / §76 N3 re-decide lead_max from it. Canon §77."""
import math

from harvest.analysis import latency as L


def test_constant_latency_matches_the_single_latency_count():
    lats = [0.307] * 60
    assert L.step_votes(lats, T_c=0.33, lead_max=1.0, d_hat=0.307) == [3] * 20
    assert L.step_votes(lats, T_c=0.33, lead_max=1.5, d_hat=0.307) == [4] * 15
    assert L.votes_per_step(0.307, 0.33, 1.0) == 3 and L.votes_per_step(0.307, 0.33, 1.5) == 4


def test_failures_and_slow_answers_do_not_count_and_the_median_is_reported():
    # asks at -1.5, -1.17, -0.84, -0.51 (d_hat 0.4) with latencies 0.3, failure, 0.9, 0.6: only the first answer
    # arrives before the step starts
    assert L.step_votes([0.3, None, 0.9, 0.6], T_c=0.33, lead_max=1.5, d_hat=0.4) == [1]
    j = L.judgment4([0.307] * 60 + [None] * 60, T_c=0.33, d_hat=0.307)
    assert j["lead1.5"]["n_steps"] == 30 and j["lead1.5"]["median"] == 2.0
    assert j["lead1.5"]["la2_possible"] is True and j["rule"].startswith("median")
    assert math.isclose(j["d_hat"], 0.307)


def test_judge_e0_reports_judgment4():
    rows = [{"size": "S1", "N": 1, "slot": 0, "site": "pod", "phase": "closed", "ok": True, "lat": 0.2}] * 40
    out = L.judge_e0(rows)
    assert out["j4"]["lead1.5"]["median"] == 4.0 and out["j4"]["lead1.0"]["median"] == 3.0
