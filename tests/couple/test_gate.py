import json

from harvest.couple.gate import gate_answer
from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.schema import parse_answer

P = CoupleParams()


def _g(d, t1=None, age=2.0, mode="F0"):
    a = parse_answer(json.dumps(d), mode, P.cameras, 1, 10.0, 10.0 + age)
    return gate_answer(a, P, t1 or {})


def test_uncertain_or_low_confidence_edit_becomes_continue():
    a = _g(answer("edit", execution="uncertain", intent="misaligned", dp=(0, 0, 0.02)))
    assert (a.command, a.gate, a.edit) == ("continue", "uncertain", None)
    b = _g(answer("edit", execution="failed", confidence="low", dp=(0, 0, 0.02)))
    assert (b.command, b.gate) == ("continue", "uncertain")


def test_edit_needs_failed_or_misaligned():
    a = _g(answer("edit", execution="progressing", intent="aligned", dp=(0, 0, 0.02)))
    assert (a.command, a.gate) == ("continue", "no_takeover_reason")
    b = _g(answer("edit", execution="failed", dp=(0, 0, 0.02)))
    assert (b.command, b.gate, b.takeover_ok) == ("edit", "ok", True)


def test_stale_edit_keeps_only_the_assessment():
    a = _g(answer("edit", execution="failed", dp=(0, 0, 0.02)), age=15.5)
    assert (a.command, a.gate, a.edit) == ("continue", "stale", None) and a.execution == "failed"


def test_edit_without_evidence_is_dropped():
    a = _g(answer("edit", execution="failed", evidence="", dp=(0, 0, 0.02)))
    assert (a.command, a.gate) == ("continue", "no_evidence")
    b = _g(answer("edit", execution="failed", views=(), dp=(0, 0, 0.02)))
    assert b.gate == "no_evidence"


def test_claims_need_the_active_wrist_and_agree_with_t1():
    a = _g(answer(claims=(("grasped", "cam_head"), ("grasped", "cam_wrist_left"), ("grasped", "cam_wrist_right"))),
           t1={"holding_t": True})
    assert a.claims == (("grasped", "cam_wrist_right"),)
    assert "head_only_claim:grasped" in a.notes and "other_wrist_claim:grasped" in a.notes
    b = _g(answer(claims=(("grasped", "cam_wrist_right"),)), t1={"holding_t": False})
    assert b.claims == () and "claim_vs_t1:grasped" in b.notes
    c = _g(answer(claims=(("placed", "cam_wrist_right"),)), t1={"holding_t": True})
    assert c.claims == ()
    d = _g(answer(claims=(("grasped", "cam_wrist_right"),)), t1={"holding_t": None})
    assert d.claims == (("grasped", "cam_wrist_right"),)


def test_stop_needs_a_wrist_placed_or_released_claim():
    a = _g(answer("stop", execution="progressing"))
    assert (a.command, a.gate) == ("continue", "stop_without_wrist_claim")
    b = _g(answer("stop", claims=(("placed", "cam_wrist_right"),)), t1={"holding_t": False})
    assert (b.command, b.gate) == ("stop", "ok")


def test_progress_claims_without_wrist_view_are_not_trusted():
    a = _g(answer(done=("grasped the mug",), views=("cam_head",)))
    assert a.progress_trusted is False and "progress_claim_without_wrist" in a.notes
    b = _g(answer(done=("grasped the mug",)))
    assert b.progress_trusted is True


def test_keep_takeover_flag():
    a = _g(answer(diff="keep", execution="failed"), mode="F1")
    assert a.command == "continue" and a.takeover_ok is True and a.gate == "ok"
    b = _g(answer(diff="keep", execution="failed"), mode="F1", age=16.0)
    assert b.takeover_ok is False and "stale_keep" in b.notes
