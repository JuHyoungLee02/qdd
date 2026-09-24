"""M4 overlap-commit ledger (design/M4-overlap-commit.md §4.1-§4.3, §4.6)."""
import pytest

from harvest.runtime.m4 import CommitLedger, M4Params, Vote


def _v(ds, choice, t_state, call="c", epoch=0, q="dir_xy", t_recv=None):
    return Vote(ds=ds, question=q, choice=choice, p_chosen=0.9, call_id=call, t_send=t_state,
                t_recv=t_state + 0.3 if t_recv is None else t_recv, t_state=t_state, premise_epoch=epoch)


def _led(**kw):
    return CommitLedger(M4Params(T_c=0.33, **kw), questions=("dir_xy", "mag_coarse", "phase"))


def test_target_slots_first_after_dhat_then_H():
    L = _led(H=3, d_p95_init=0.30)
    # t_send 0.10 + d 0.30 = 0.40 -> first slot start >= 0.40 is ds 2 (0.66)
    assert L.target_slots(0.10) == [2, 3, 4]
    L1 = _led(H=1, d_p95_init=0.30)
    assert L1.target_slots(0.0) == [1]


def test_first_vote_tentative_then_LA2_commits():
    L = _led()
    assert L.on_vote(_v(5, "plus_x", 0.5, "a"), now=0.8) == "tentative"
    assert L.slot("dir_xy", 5).status == "TENTATIVE"
    assert L.on_vote(_v(5, "plus_x", 0.83, "b"), now=1.1) == "agree"
    L.try_commit_prefix("dir_xy", now=1.1)
    assert L.slot("dir_xy", 5).status == "COMMITTED"
    assert L.decision("dir_xy", 5) == ("plus_x", "COMMITTED")


def test_commit_only_prefix_in_order():
    L = _led()
    L.on_vote(_v(6, "plus_x", 0.5, "a"), now=0.8)
    L.on_vote(_v(6, "plus_x", 0.83, "b"), now=0.9)
    L.on_vote(_v(5, "plus_y", 0.83, "b"), now=0.9)  # slot 5 has a single vote -> not committable
    L.try_commit_prefix("dir_xy", now=0.9)
    assert L.slot("dir_xy", 5).status == "TENTATIVE"
    assert L.slot("dir_xy", 6).status == "TENTATIVE"  # blocked behind slot 5 (#1 prefix only)


def test_challenger_needs_defer_window_W1():
    L = _led(W=1, n_la=5)  # disable LA2 commit to watch the challenge logic
    L.on_vote(_v(5, "plus_x", 0.1, "a"), now=0.4)
    assert L.on_vote(_v(5, "minus_x", 0.43, "b"), now=0.7) == "challenger"
    assert L.slot("dir_xy", 5).status == "CONTESTED"
    assert L.slot("dir_xy", 5).incumbent == "plus_x"
    assert L.on_vote(_v(5, "minus_x", 0.76, "c"), now=1.0) == "replaced"
    assert L.slot("dir_xy", 5).incumbent == "minus_x"


def test_irreversible_choice_gets_W_plus_1():
    L = _led(W=1, n_la=5)
    L.on_vote(_v(5, "continue", 0.1, "a", q="phase"), now=0.4)
    irr = lambda q, c: c == "next"
    assert L.on_vote(_v(5, "next", 0.43, "b", q="phase"), now=0.7, irreversible=irr) == "challenger"
    assert L.on_vote(_v(5, "next", 0.76, "c", q="phase"), now=1.0, irreversible=irr) == "defer"
    assert L.on_vote(_v(5, "next", 1.09, "d", q="phase"), now=1.3, irreversible=irr) == "replaced"


def test_premise_epoch_and_stale_votes_dropped():
    L = _led(stale_max=1.5)
    L.bump_epoch("astra_patch", now=0.2)
    assert L.on_vote(_v(9, "plus_x", 0.1, "a", epoch=0), now=0.5) == "dropped_epoch"
    assert L.on_vote(_v(9, "plus_x", 0.1, "a", epoch=1), now=1.7) == "dropped_stale"
    assert L.on_vote(_v(9, "plus_x", 1.0, "a", epoch=1), now=1.7) == "tentative"


def test_frozen_or_committed_slot_is_log_only():
    L = _led()
    L.on_vote(_v(2, "plus_x", 0.1, "a"), now=0.3)
    # slot 2 starts at 0.66: a vote arriving at 0.7 is too late (FROZEN)
    assert L.on_vote(_v(2, "minus_x", 0.2, "b"), now=0.7) == "log_only"
    assert L.slot("dir_xy", 2).incumbent == "plus_x"


def test_gamma_vote_commit():
    L = _led(n_la=9, gamma=0.67)
    for i, c in enumerate(["plus_x", "plus_y", "plus_x", "plus_x"]):
        L.on_vote(_v(8, c, 0.1 + 0.33 * i, f"c{i}"), now=0.2 + 0.33 * i)
    L.try_commit_prefix("dir_xy", now=1.5)
    assert L.slot("dir_xy", 8).status == "COMMITTED"


def test_ordinal_tau_agreement_for_mag():
    L = _led(n_la=2, tau=1)
    L.on_vote(_v(5, "medium", 0.1, "a", q="mag_coarse"), now=0.4)
    assert L.on_vote(_v(5, "large", 0.43, "b", q="mag_coarse"), now=0.7) == "agree"  # adjacent bin, tau 1
    L0 = _led(n_la=2, tau=0)
    L0.on_vote(_v(5, "medium", 0.1, "a", q="mag_coarse"), now=0.4)
    assert L0.on_vote(_v(5, "large", 0.43, "b", q="mag_coarse"), now=0.7) == "challenger"


def test_deviate_bumps_epoch_and_reopens_future_uncommitted():
    L = _led()
    L.on_vote(_v(9, "plus_x", 1.0, "a"), now=1.3)
    out = L.on_step_executed(3, "DEVIATE", now=1.32)
    assert out["epoch"] == 1 and out["early_call"] and not out["hold"]
    assert L.slot("dir_xy", 9).status == "OPEN" and L.slot("dir_xy", 9).votes == []


def test_contradict_holds_and_drops():
    L = _led()
    L.on_vote(_v(9, "plus_x", 1.0, "a"), now=1.3)
    out = L.on_step_executed(3, "CONTRADICT", now=1.32)
    assert out["hold"] and out["early_call"] and L.epoch == 1


def test_bad_outcome_gate_replaces_at_once():
    L = _led(W=2, n_la=9)
    L.on_vote(_v(9, "plus_x", 1.0, "a"), now=1.3)
    L.on_step_executed(3, "LAG", now=1.35)  # LAG: no epoch change, choices kept
    assert L.epoch == 0 and L.slot("dir_xy", 9).incumbent == "plus_x"
    L.last_bad_t = 1.4  # a (b) != OK signal after the incumbent was set (gate_hard)
    assert L.on_vote(_v(9, "minus_x", 1.4, "b"), now=1.6) == "replaced"


def test_decision_and_unconfirmed_accounting():
    L = _led()
    L.on_vote(_v(4, "plus_x", 0.1, "a"), now=0.4)
    assert L.decision("dir_xy", 4) == ("plus_x", "TENTATIVE")
    L.mark_executed(4, now=4 * 0.33)
    st = L.stats()
    assert st["executed"]["dir_xy"] == 1 and st["unconfirmed_executed"]["dir_xy"] == 1
    assert st["commit_ratio"]["dir_xy"] == 0.0
    assert L.decision("dir_xy", 7) == (None, "EMPTY")


def test_latency_window_updates_dhat_and_nmax():
    L = _led(d_p95_init=0.30)
    assert L.n_max() == 2  # ceil(0.30/0.33)+1
    for x in [0.5] * 60:
        L.record_latency(x)
    assert L.d_hat == pytest.approx(0.5)
    assert L.n_max() == 3


def test_flip_score_tv_distance():
    L = _led(flip_win=2)
    for i, c in enumerate(["plus_x", "plus_x", "minus_x", "minus_x"]):
        L.on_vote(_v(20 + i, c, 0.33 * i, f"c{i}"), now=0.33 * i + 0.1)
    assert L.flip_score["dir_xy"] == pytest.approx(1.0)
