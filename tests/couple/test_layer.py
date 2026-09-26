import json

import pytest

from harvest.couple.gate import gate_answer
from harvest.couple.layer import AstraLayer
from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.schema import parse_answer

P0, P1 = CoupleParams(request_mode="F0"), CoupleParams(request_mode="F1")


def _a(d, no, p=P0, t1=None):
    return gate_answer(parse_answer(json.dumps(d), p.request_mode, p.cameras, no, 0.0, 2.0), p, t1 or {})


def _edit(dp, **kw):
    return answer("edit", execution="failed", dp=dp, **kw)


def test_single_then_confirmed_edit():
    L = AstraLayer(P0)
    r1 = L.on_answer(_a(_edit((0, 0, 0.02)), 1))
    assert (r1.action, r1.key, r1.weight) == ("apply", 1, 0.5)
    assert L.flow_last()["state"] == "unconfirmed"
    r2 = L.on_answer(_a(_edit((0, 0.004, 0.02)), 2))  # 11 deg apart: same
    assert (r2.action, r2.key, r2.weight) == ("confirm", 1, 1.0)
    assert L.flow_last()["state"] == "confirmed"


def test_different_direction_is_a_new_candidate_and_opposite_is_a_flip():
    L = AstraLayer(P0)
    L.on_answer(_a(_edit((0.02, 0, 0)), 1))
    r = L.on_answer(_a(_edit((0.02, 0.02, 0)), 2))  # 45 deg: not the same, not a flip
    assert (r.action, r.key, r.weight) == ("apply", 2, 0.5)
    f = L.on_answer(_a(_edit((-0.02, -0.02, 0)), 3))
    assert (f.action, f.key, f.weight) == ("flip", 3, 0.0)
    c = L.on_answer(_a(_edit((-0.02, -0.021, 0)), 4))
    assert (c.action, c.key, c.weight) == ("confirm", 3, 1.0)


def test_a_continue_between_two_edits_breaks_the_confirmation():
    L = AstraLayer(P0)
    L.on_answer(_a(_edit((0, 0, 0.02)), 1))
    assert L.on_answer(_a(answer("continue"), 2)).action == "none"
    assert L.on_answer(_a(_edit((0, 0, 0.02)), 3)).action == "apply"


def test_gripper_change_is_not_the_same_edit():
    L = AstraLayer(P0)
    L.on_answer(_a(_edit((0, 0, 0.02)), 1))
    assert L.on_answer(_a(_edit((0, 0, 0.02), gripper="open"), 2)).action == "apply"


def test_f1_keep_confirms_only_with_a_takeover_reason():
    L = AstraLayer(P1)
    L.on_answer(_a(answer("edit", diff="revise", execution="failed", dp=(0.01, 0, 0)), 1, P1))
    assert L.on_answer(_a(answer(diff="keep", execution="uncertain"), 2, P1)).action == "none"
    L.on_answer(_a(answer("edit", diff="revise", execution="failed", dp=(0.01, 0, 0)), 3, P1))
    r = L.on_answer(_a(answer(diff="keep", execution="failed"), 4, P1))
    assert (r.action, r.key, r.weight) == ("confirm", 3, 1.0)


def test_stop_needs_two_answers():
    L = AstraLayer(P0)
    s = answer("stop", claims=(("placed", "cam_wrist_right"),))
    assert L.on_answer(_a(s, 1, t1={"holding_t": False})).action == "stop_claim"
    assert L.on_answer(_a(s, 2, t1={"holding_t": False})).action == "stop_confirmed"
    assert L.counts["stop_confirmed"] == 1


def test_progress_only_from_trusted_answers():
    L = AstraLayer(P0)
    L.on_answer(_a(answer(done=("grasped the mug",)), 1))
    assert L.progress["verified_completed"] == ["grasped the mug"]
    L.on_answer(_a(answer(done=("placed the mug",), views=("cam_head",)), 2))
    assert L.progress["verified_completed"] == ["grasped the mug"]
    assert pytest.approx(P0.single_weight) == 0.5
