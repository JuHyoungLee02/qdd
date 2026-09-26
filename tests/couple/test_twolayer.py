import json

import numpy as np

from harvest.couple.gate import gate_answer
from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.schema import parse_answer
from harvest.couple.twolayer import (NoProgress, TwoLayerGate, VlaFastCheck, adherence_cos, committed_vector,
                                      follows)

P = CoupleParams()
T1_CLOSE = {"gripper_open": True, "holding_t": False}


def _a(d, t1=None):
    return gate_answer(parse_answer(json.dumps(d), "F0", P.cameras, 1, 0.0, 2.0), P, t1 or {})


def test_params_adhere_cos_default():
    assert P.adhere_cos == 0.5


def test_fresh_misaligned_or_failed_or_opposite_gripper_vetoes():
    g = TwoLayerGate(P)
    assert g.allow("close", 10.0, _a(answer(intent="misaligned")), 9.0, T1_CLOSE, True) == (False, "astra_misaligned")
    assert g.allow("close", 10.0, _a(answer(execution="failed")), 9.0, T1_CLOSE, True) == (False, "astra_failed")
    op = _a(answer("edit", execution="failed", dp=(0, 0, 0.01), gripper="open"))
    assert g.allow("close", 10.0, op, 9.0, T1_CLOSE, True) == (False, "astra_gripper_opposes")
    low = _a(answer(intent="misaligned", confidence="low"))
    assert g.allow("close", 10.0, low, 9.0, T1_CLOSE, True) == (True, "t1_fresh")


def test_stale_astra_lets_the_vla_flow_with_t1_evidence():
    g = TwoLayerGate(P)
    old = _a(answer(intent="misaligned"))
    assert g.allow("close", 20.0, old, 16.9, T1_CLOSE, True) == (True, "t1_astra_stale")
    assert g.allow("close", 20.0, None, None, T1_CLOSE, False) == (False, "no_evidence")
    assert g.allow("stage", 20.0, None, None, {"holding_t": True}, False) == (True, "t1_astra_stale")
    assert g.allow("release", 20.0, None, None, {"holding_t": False}, True) == (False, "no_evidence")


def test_wrist_claim_is_reference_only():
    g = TwoLayerGate(P)
    a = _a(answer(claims=(("grasp_ready", "cam_wrist_right"),)))
    assert g.allow("close", 10.0, a, 9.5, {"gripper_open": True}, False) == (False, "no_evidence")
    assert g.allow("close", 10.0, a, 9.5, {"gripper_open": True, "holding_t": False}, True) == (True, "t1_fresh")


def test_strict_reading_needs_aligned():
    g = TwoLayerGate(CoupleParams(irrev_need_aligned=True))
    assert g.allow("close", 10.0, _a(answer(intent="uncertain")), 9.5, T1_CLOSE, True) == (False, "astra_not_aligned")


def test_mismatch_event_once_after_1_s_of_blocking():
    g = TwoLayerGate(P)
    bad = _a(answer(intent="misaligned"))
    g.allow("close", 10.0, bad, 9.9, T1_CLOSE, True)
    assert not g.mismatch_due("close", 10.5)
    g.allow("close", 11.0, bad, 10.9, T1_CLOSE, True)
    assert g.mismatch_due("close", 11.0) and not g.mismatch_due("close", 11.2)
    assert g.counts["deny:astra_misaligned"] == 1 and len(g.log) == 1


def test_committed_vector_and_fast_check():
    assert committed_vector({"dir_xy": "plus_x", "dir_z": "down"}).tolist() == [1, 0, -1]
    assert committed_vector({"dir_xy": "none_xy"}) is None
    f = VlaFastCheck(P)
    back = np.array([-1.0, 0.0, 0.0])
    fired = [f.on_step(back, np.array([1.0, 0, 0])) for _ in range(3)]
    assert fired == [False, False, True]
    assert f.on_step(np.array([1.0, 0, 0]), np.array([1.0, 0, 0])) is False


def test_adherence_cos_basic_values():
    assert adherence_cos(np.array([1.0, 0, 0]), np.array([2.0, 0, 0])) == 1.0
    assert adherence_cos(np.array([-1.0, 0, 0]), np.array([1.0, 0, 0])) == -1.0
    assert adherence_cos(np.array([0.0, 1.0, 0]), np.array([1.0, 0, 0])) == 0.0
    assert adherence_cos(np.array([0.0, 0.0, 0.0]), np.array([1.0, 0, 0])) is None
    assert adherence_cos(None, np.array([1.0, 0, 0])) is None
    assert adherence_cos(np.array([1.0, 0, 0]), None) is None


def test_follows_threshold_at_0p5():
    p = CoupleParams()
    on_axis = np.array([1.0, 0.0, 0.0])
    just_over = np.array([0.6, 0.8, 0.0])  # cos = 0.6 > 0.5
    just_under = np.array([0.3, 0.9539, 0.0])  # cos ~ 0.3 < 0.5
    assert follows(on_axis, on_axis, p) is True
    assert follows(just_over, on_axis, p) is True
    assert follows(just_under, on_axis, p) is False
    assert follows(np.zeros(3), on_axis, p) is None


def test_fast_check_zero_vector_does_not_crash_and_resets():
    f = VlaFastCheck(P)
    back = np.array([-1.0, 0.0, 0.0])
    axis = np.array([1.0, 0, 0])
    assert f.on_step(back, axis) is False
    assert f.on_step(back, axis) is False
    assert f.on_step(np.zeros(3), axis) is False  # no information: resets, does not fire, does not crash
    assert f.n == 0
    assert f.on_step(back, axis) is False
    assert f.on_step(back, axis) is False
    assert f.on_step(back, axis) is True


def test_no_progress_when_the_tip_does_not_follow_the_offset():
    n = NoProgress(P)
    fired = []
    for i in range(301):
        t = i * 0.01
        fired.append(n.update(t, np.zeros(3), np.array([0.0, 0.0, 0.01 * t])))
    assert any(fired)
    m = NoProgress(P)
    assert not any(m.update(i * 0.01, np.array([0, 0, 0.01 * i * 0.01]), np.array([0, 0, 0.01 * i * 0.01]))
                   for i in range(301))
