"""Segment-plan agreement and the a = 0 freeze in the Astra layer (plan 2026-09-26 Task 18, canon §90 caution): the
agreed plan changes only when two consecutive gated answers give the same new plan; near contact (authority a == 0
at delivery) an agreed `do` is not changed (plan_frozen), now / next may update when `do` is unchanged."""
import json

from harvest.couple.gate import gate_answer
from harvest.couple.layer import AstraLayer
from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.schema import parse_answer

P = CoupleParams()
A = {"now": "approach", "do": "none", "next": "descend"}
D = {"now": "descend", "do": "none", "next": "grasp"}
G = {"now": "grasp", "do": "close", "next": "lift"}


def _a(seg, no, cmd="continue", **kw):
    d = answer(cmd, segment=seg, **kw)
    return gate_answer(parse_answer(json.dumps(d), "F0", P.cameras, no, 0.0, 2.0, version="v2"), P, {})


def test_plan_needs_two_consecutive_answers():
    L = AstraLayer(P)
    assert L.plan is None and L.on_answer(_a(A, 1)).plan == "plan_candidate" and L.plan is None
    assert L.on_answer(_a(A, 2)).plan == "plan_agreed" and L.plan == A
    assert L.on_answer(_a(D, 3)).plan == "plan_candidate" and L.plan == A  # one deviating answer: logged only
    assert L.on_answer(_a(G, 4)).plan == "plan_candidate" and L.plan == A  # a different one resets the candidate
    assert L.on_answer(_a(A, 5)).plan == "plan_same" and L.plan == A
    assert L.on_answer(_a(D, 6)).plan == "plan_candidate"
    assert L.on_answer(_a(D, 7)).plan == "plan_agreed" and L.plan == D
    assert L.counts["plan_agreed"] == 2 and L.counts["plan_candidate"] == 4


def test_plan_agreement_is_independent_of_the_edit_agreement():
    L = AstraLayer(P)
    r1 = L.on_answer(_a(A, 1, "edit", execution="failed", dp=(0, 0.02, 0)))
    r2 = L.on_answer(_a(A, 2, "edit", execution="failed", dp=(0, 0.02, 0)))
    assert (r1.action, r1.plan, r2.action, r2.plan) == ("apply", "plan_candidate", "confirm", "plan_agreed")
    assert L.flow_last()["segment"] == A and L.flow_last()["state"] == "confirmed"


def test_a0_freezes_an_agreed_do_but_lets_now_next_update():
    L = AstraLayer(P)
    L.on_answer(_a(D, 1))
    L.on_answer(_a(D, 2))
    assert L.plan == D
    r1, r2 = L.on_answer(_a(G, 3), authority=0.0), L.on_answer(_a(G, 4), authority=0.0)
    assert (r1.plan, r2.plan) == ("plan_candidate", "plan_frozen") and L.plan == D and L.counts["plan_frozen"] == 1
    same_do = {"now": "grasp", "do": "none", "next": "lift"}  # do unchanged (none) -> now / next may update
    L.on_answer(_a(same_do, 5), authority=0.0)
    assert L.on_answer(_a(same_do, 6), authority=0.0).plan == "plan_agreed" and L.plan == same_do
    # away from contact (a > 0) the held change goes through on the next agreeing pair
    L.on_answer(_a(G, 7), authority=0.4)
    assert L.on_answer(_a(G, 8), authority=0.4).plan == "plan_agreed" and L.plan == G


def test_first_plan_at_a0_is_agreed_and_v1_answers_carry_no_plan():
    L = AstraLayer(P)
    L.on_answer(_a(G, 1), authority=0.0)
    assert L.on_answer(_a(G, 2), authority=0.0).plan == "plan_agreed"  # nothing agreed before: nothing to freeze
    v1 = gate_answer(parse_answer(json.dumps(answer("continue")), "F0", P.cameras, 3, 0.0, 2.0), P, {})
    assert L.on_answer(v1).plan is None and L.plan == G and "segment" in L.flow_last()
    assert "segment" not in AstraLayer(P).flow_last()
