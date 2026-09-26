import pytest

from harvest.couple.recovery_cache import FailSig, RecoveryCache, falsified

SIG = FailSig("S1", "o3", "grasp_miss", "t1_skill")
REC = {"lever": "dp.approach_dir", "value": "side_front"}
FALS = [{"pred": "holding_t", "value": True}]


def test_first_seen_then_one_reuse_per_episode():
    c = RecoveryCache()
    assert c.decide(1, SIG, {"holding_t": False}, 0.0)[:2] == ("call_j2", None)
    c.remember(SIG, REC, FALS, "if the mug ends up held the miss was timing, not approach", "j2:call7", 1.0)
    d, lesson, why = c.decide(1, SIG, {"holding_t": False}, 2.0)
    assert (d, why) == ("reuse", "not_falsified") and lesson.recovery == REC
    assert c.decide(1, SIG, {"holding_t": False}, 3.0)[::2] == ("call_j2", "reuse_cap")
    assert c.decide(2, SIG, {"holding_t": False}, 4.0)[0] == "reuse"


def test_partial_signature_never_reuses():
    c = RecoveryCache()
    c.remember(SIG, REC, FALS, "x", "j2:1", 0.0)
    other = FailSig("S1", "o3", "grasp_miss", "v1h_critic")
    assert c.decide(1, other, {"holding_t": False}, 1.0)[::2] == ("call_j2", "partial_match")


def test_falsified_or_unknown_goes_to_j2_and_failed_reuse_is_recorded():
    c = RecoveryCache()
    c.remember(SIG, REC, FALS, "x", "j2:1", 0.0)
    assert c.decide(1, SIG, {"holding_t": True}, 1.0)[::2] == ("call_j2", "falsified")
    assert c.decide(2, SIG, {}, 1.0)[::2] == ("call_j2", "falsify_unknown")
    assert c.decide(3, SIG, {"holding_t": False}, 2.0)[0] == "reuse"
    c.report(3, SIG, False, 5.0)
    assert c.decide(3, SIG, {"holding_t": False}, 6.0)[::2] == ("call_j2", "reuse_failed")
    kinds = [a["event"] for a in c.audit]
    assert kinds.count("decide") == 4 and "reuse_outcome" in kinds and "remember" in kinds


def test_falsify_format_is_checked():
    assert falsified([{"pred": "on_tp", "value": False}], {"on_tp": True}) == "no"
    with pytest.raises(ValueError, match="pred"):
        RecoveryCache().remember(SIG, REC, [{"value": True}], "x", "j2:1", 0.0)
