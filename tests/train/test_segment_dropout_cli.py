"""ser-A-min-3 fix round 1 item 2: stage-A and stage-B training default to the canon §90 unknown-segment share
(SEGMENT_DROPOUT 0.3, training only); stage B composes it with the motion-line dropout and refuses resuming a run
saved before the option with the new default (that run never dropped the segment line)."""
import pytest

from harvest.intent import SEGMENT_DROPOUT


def test_stage_a_train_defaults_to_the_segment_share(monkeypatch):
    from harvest.train import stagea_train as A
    got = {}
    monkeypatch.setattr(A, "cmd_train", lambda a: got.update(vars(a)))
    A.main(["train", "--run", "x"])
    assert got["segment_dropout"] == SEGMENT_DROPOUT == 0.3
    A.main(["train", "--run", "x", "--segment-dropout", "0"])
    assert got["segment_dropout"] == 0.0


def test_stage_b_train_option_and_resume():
    T = pytest.importorskip("harvest.train.stageb_train", exc_type=ImportError)  # imports torch
    d = vars(T.build_parser().parse_args(["train", "--run", "a"]))
    assert d["segment_dropout"] == SEGMENT_DROPOUT and "segment_dropout" in T.RESUME_KEYS
    old = {k: v for k, v in d.items() if k != "segment_dropout"}  # saved before the option existed
    with pytest.raises(SystemExit, match="segment_dropout"):
        T.check_resume_args(old, d)
    T.check_resume_args(old, {**d, "segment_dropout": 0.0})
