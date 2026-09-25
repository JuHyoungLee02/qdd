"""M4 grace window W (R7 cycle 7 N2, canon §72): W = further votes for the same challenger needed after the first
challenging vote (M4 §4.2 pseudocode, §3 #3); W = 0 replaces at the first challenging vote; W < 0 is refused."""
import pytest

from harvest.runtime.m4 import CommitLedger, M4Params, Vote


def _v(ds, choice, t, call):
    return Vote(ds=ds, question="dir_xy", choice=choice, p_chosen=0.9, call_id=call, t_send=t, t_recv=t + 0.3,
                t_state=t, premise_epoch=0)


def _challenges(W, n):
    L = CommitLedger(M4Params(T_c=0.33, W=W, n_la=9), questions=("dir_xy",))
    L.on_vote(_v(20, "plus_x", 0.1, "a"), now=0.4)
    return [L.on_vote(_v(20, "minus_x", 0.1 + 0.33 * (i + 1), f"c{i}"), now=0.4 + 0.33 * (i + 1)) for i in range(n)]


def test_W0_replaces_at_the_first_challenging_vote():
    assert _challenges(0, 1) == ["replaced"]


def test_W1_default_replaces_after_two_challenging_votes():
    assert M4Params().W == 1
    assert _challenges(1, 2) == ["challenger", "replaced"]


def test_W2_replaces_after_three_challenging_votes():
    assert _challenges(2, 3) == ["challenger", "defer", "replaced"]


def test_W0_irreversible_is_W_plus_1():
    L = CommitLedger(M4Params(T_c=0.33, W=0, n_la=9), questions=("dir_xy",))
    L.on_vote(_v(20, "plus_x", 0.1, "a"), now=0.4)
    irr = lambda q, c: c == "minus_x"  # noqa: E731
    assert L.on_vote(_v(20, "minus_x", 0.43, "b"), now=0.7, irreversible=irr) == "challenger"
    assert L.on_vote(_v(20, "minus_x", 0.76, "c"), now=1.0, irreversible=irr) == "replaced"


def test_negative_W_is_refused():
    with pytest.raises(ValueError, match="W"):
        M4Params(W=-1)
