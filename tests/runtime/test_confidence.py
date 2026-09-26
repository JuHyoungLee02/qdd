"""harvest.runtime.confidence: the E-CONF decision-confidence LOGGING hook (conf-base@v1, canon §95, conf.md §5,
plan Task 22) -- a pure function of ModelResult.answers {p_chosen, p_second}, no gate, no forward pass."""
import math
import time

import pytest

from harvest.runtime.confidence import VER, conf_from_answers


def _ans(**qs):
    """{question: {"p_chosen": .., "p_second": ..}} -> a minimal answers dict (choice/probs/qid not needed here)."""
    return {q: {"p_chosen": p1, "p_second": p2} for q, (p1, p2) in qs.items()}


def test_empty_answers_records_nothing():
    assert conf_from_answers({}) is None


def test_selector_missing_confidence_fields_records_nothing():
    """Modular backend without p_chosen / p_second (canon §95: record only if the selector returns those fields)."""
    assert conf_from_answers({"dir_xy": {"choice": "plus_x"}}) is None
    assert conf_from_answers({"dir_xy": {"p_chosen": 0.9}}) is None  # p_second missing


def test_ordinary_two_questions_matches_the_formula():
    a = _ans(dir_xy=(0.7, 0.2), mag_coarse=(0.9, 0.05))
    c = conf_from_answers(a)
    assert c["ver"] == VER
    assert c["per_q"]["dir_xy"]["top1"] == 0.7 and c["per_q"]["dir_xy"]["top2"] == 0.2
    m_xy = math.log(0.7 / 0.2)
    m_mag = math.log(0.9 / 0.05)
    assert c["per_q"]["dir_xy"]["margin"] == pytest.approx(m_xy)
    assert c["per_q"]["mag_coarse"]["margin"] == pytest.approx(m_mag)
    assert "margin_inf" not in c["per_q"]["dir_xy"] and "margin_inf" not in c["per_q"]["mag_coarse"]
    # dir_xy has the smaller margin -> it is the argmin
    assert m_xy < m_mag and c["argmin_q"] == "dir_xy" and c["min_margin"] == pytest.approx(m_xy)
    assert c["joint"] == pytest.approx(-math.log(0.7) - math.log(0.9))
    assert "joint_inf" not in c


def test_p_second_zero_single_option_and_mock_selector_are_the_same_plus_inf_case():
    """Single-option questions and mock selectors (models.py:120 p_chosen=1.0 / p_second=0.0) both hit p_second==0:
    margin -> null + margin_inf=+1 (maximally confident, never blamed as the argmin unless every question ties)."""
    a = _ans(target=(1.0, 0.0))
    c = conf_from_answers(a)
    assert c["per_q"]["target"]["margin"] is None and c["per_q"]["target"]["margin_inf"] == 1
    assert c["argmin_q"] == "target"  # only question, so it is the argmin by default
    assert c["min_margin"] is None
    assert c["joint"] == pytest.approx(0.0)  # -ln(1.0) = 0, finite (p_chosen > 0)


def test_p_chosen_zero_dominates_the_argmin_even_against_other_inf_questions():
    """p_chosen == 0 -> margin -inf (checked before p_second, conf.md §5: "no evidence on the chosen option" is the
    worst case regardless of p_second) and always wins the min -- including against a p_second==0 (+inf) question."""
    a = _ans(dir_xy=(1.0, 0.0), mag_coarse=(0.0, 0.3), target=(0.5, 0.5))
    c = conf_from_answers(a)
    assert c["per_q"]["mag_coarse"]["margin"] is None and c["per_q"]["mag_coarse"]["margin_inf"] == -1
    assert c["argmin_q"] == "mag_coarse" and c["min_margin"] is None
    assert c["joint"] is None and c["joint_inf"] is True  # -ln(0) term makes the joint non-finite too


def test_p_chosen_and_p_second_both_zero_is_treated_as_the_minus_inf_case():
    a = _ans(dir_xy=(0.0, 0.0))
    c = conf_from_answers(a)
    assert c["per_q"]["dir_xy"]["margin"] is None and c["per_q"]["dir_xy"]["margin_inf"] == -1


def test_none_escalate_choice_is_scored_like_any_other_option():
    """NE = "NONE_ESCALATE" (models.py) is not excluded from the record (conf.md §5)."""
    a = {"phase": {"choice": "NONE_ESCALATE", "p_chosen": 0.4, "p_second": 0.35}}
    c = conf_from_answers(a)
    assert c["per_q"]["phase"]["margin"] == pytest.approx(math.log(0.4 / 0.35))


def test_argmin_tie_break_is_the_first_question_in_order():
    """Two questions with the identical finite margin: the earlier one in `answers` (question order) wins."""
    a = _ans(dir_xy=(0.6, 0.3), dir_z=(0.4, 0.2))  # both ln(2) = same margin
    c = conf_from_answers(a)
    assert c["per_q"]["dir_xy"]["margin"] == pytest.approx(c["per_q"]["dir_z"]["margin"])
    assert c["argmin_q"] == "dir_xy"
    # reversed insertion order -> the new first question wins instead (order-only tie-break, not question name)
    a2 = _ans(dir_z=(0.4, 0.2), dir_xy=(0.6, 0.3))
    assert conf_from_answers(a2)["argmin_q"] == "dir_z"


def test_all_questions_plus_inf_ties_keep_question_order_too():
    a = _ans(dir_xy=(1.0, 0.0), dir_z=(1.0, 0.0))
    assert conf_from_answers(a)["argmin_q"] == "dir_xy"


def test_conf_is_json_serialisable():
    import json
    a = _ans(dir_xy=(1.0, 0.0), mag_coarse=(0.0, 0.3), target=(0.7, 0.2))
    json.dumps(conf_from_answers(a))  # raises on inf / nan -- must not appear anywhere in the record


def test_compute_cost_is_far_under_the_0_1_ms_budget():
    """Cost bound (conf.md §5, plan Task 22): p95 compute < 0.1 ms on local Python. Reported, not asserted at that
    exact flaky threshold -- a generous 2 ms sanity bound instead (catches a gross regression only)."""
    a = _ans(dir_xy=(0.7, 0.2), dir_z=(0.6, 0.3), mag_coarse=(0.9, 0.05), target=(1.0, 0.0), phase=(0.4, 0.35),
             gripper=(0.55, 0.4))
    n = 5000
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        conf_from_answers(a)
        times.append(time.perf_counter() - t0)
    times.sort()
    p95_ms = times[int(n * 0.95)] * 1e3
    print(f"conf_from_answers p95 over {n} calls (6 questions): {p95_ms:.5f} ms")
    assert p95_ms < 2.0
