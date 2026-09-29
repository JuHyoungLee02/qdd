"""Critic violation score from predicate probabilities (pure part of harvest.m4b.analyze)."""
import pytest

from harvest.m4b.analyze import viol_prob


def test_viol_prob_max_over_expected_in_scope():
    p = {"holding_t": 0.9, "gripper_open": 0.2, "lifted_holding": 0.7, "lifted_t": 0.4}
    # carry expects holding, not open, lifted_holding, lifted_t
    assert viol_prob("carry", p, scope=None) == pytest.approx(0.6)  # 1 - P(lifted_t)
    assert viol_prob("carry", p, scope={"holding_t", "gripper_open"}) == pytest.approx(0.2)
    assert viol_prob("close", p, scope=None) == 0.0


def test_viol_prob_or_entry_and_missing():
    p = {"holding_t": 1.0, "gripper_open": 0.0, "above_tp": 0.3, "contact_tp": 0.8}
    assert viol_prob("place_descend", p, scope=None) == pytest.approx(0.2)
    assert viol_prob("place_descend", {"holding_t": 1.0}, scope=None) == pytest.approx(0.0)  # unmeasured = no vote
    assert viol_prob("retreat", {"on_tp": None, "holding_t": 0.1}, scope=None) == pytest.approx(0.1)
