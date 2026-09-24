import re

from harvest.jevcall import DIR_XY, DIR_Z, MAG, PROGRESS, build_choice, build_request
from harvest.options import Option

FORBIDDEN = {"yes", "no", "true", "false", "ok", "fail", "failure", "failed", "accept", "reject",
             "good", "bad", "safe", "correct", "valid"}


def test_criteria_order_and_model():
    opts = [Option("up", "up", "Move up."), Option("down", "down", "Move down.")]
    k, q = build_choice("ds1.dir_z", "Which way?", opts)
    req = build_request("s  a\r\n", [(k, q)])
    assert req["model"] == "jev-1.13.0"
    assert list(req["questions"]["ds1.dir_z"]["criteria"]) == ["up", "down"]
    assert req["state"] == "s a"


def test_shown_names_obey_r1_forbidden_words():
    for opts in (DIR_XY, DIR_Z, MAG, PROGRESS):
        for o in opts:
            parts = set(re.split(r"[_\W]+", o.name.lower()))
            assert not (parts & FORBIDDEN), o.name
            assert o.desc


def test_progress_keeps_canonical_option_keys():
    assert [o.key for o in PROGRESS] == ["valid_progress", "allowed_change", "failure", "recovering", "NONE_ESCALATE"]
