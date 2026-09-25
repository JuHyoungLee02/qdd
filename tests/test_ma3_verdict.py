"""E-MA3 verdict rule (prereg_ma3 §6): boundaries with CMP_EPS; the chunk bound strictly > 0."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "se2e"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "ma3"))
import ma3_verdict as MV  # noqa: E402


def test_rule_boundaries():
    assert MV.MIN_REL == 0.05 and MV.ACC_MARGIN == 0.01 and MV.MAX_P95_INC == 0.10
    assert MV.rule(0.05, 1e-9, -0.01, 1.10)["adopt"]
    assert not MV.rule(0.0499, 0.01, 0.0, 1.0)["adopt"]
    assert not MV.rule(0.06, 0.0, 0.0, 1.0)["adopt"]
    assert not MV.rule(0.06, 0.01, -0.0101, 1.0)["adopt"]
    assert not MV.rule(0.06, 0.01, 0.0, 1.1001)["adopt"]
