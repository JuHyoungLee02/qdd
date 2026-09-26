"""astra-couple@v2 answers (plan 2026-09-26 Task 18): the segment plan is required and checked against the serialize
vocabularies, an edit needs valid_until, the stated limit 0.04 m keeps the parser tolerance 0.05 m, and an F1 keep
ignores an accompanying edit (prompt health F9) instead of a schema error."""
import pytest

from harvest.couple.mock import answer
from harvest.couple.schema import SchemaError, parse_answer

CAMS = ("cam_head", "cam_wrist_left", "cam_wrist_right")
SEG = {"now": "approach", "do": "none", "next": "descend"}


def _p(d, mode="F0", version="v2"):
    return parse_answer(d, mode, CAMS, 2, 0.0, 9.0, version=version)


def _j(d):
    import json
    return json.dumps(d)


def test_v2_parses_segment_and_valid_until():
    a = _p(_j(answer("edit", execution="failed", dp=(0.0, 0.03, 0.0), segment=SEG, valid_until="segment_end")))
    assert a.segment == SEG and a.valid_until == "segment_end" and a.command == "edit"
    b = _p(_j(answer("continue", segment={"now": "grasp", "do": "close", "next": "lift"})))
    assert b.segment["do"] == "close" and b.valid_until is None


@pytest.mark.parametrize("seg", [None, {"now": "place_descend", "do": "none", "next": "release"},
                                 {"now": "approach", "do": "grab", "next": "descend"},
                                 {"now": "approach", "do": "none"}, "approach"])
def test_v2_refuses_a_missing_or_off_vocabulary_segment(seg):
    d = answer("continue")
    if seg is None:
        d.pop("segment", None)
    else:
        d["segment"] = seg
    with pytest.raises(SchemaError, match="segment"):
        _p(_j(d))


def test_v2_edit_needs_valid_until_and_keeps_the_005_tolerance():
    d = answer("edit", execution="failed", dp=(0.0, 0.0, 0.045))
    d["edit"].pop("valid_until")
    with pytest.raises(SchemaError, match="valid_until"):
        _p(_j(d))
    d["edit"]["valid_until"] = "forever"
    with pytest.raises(SchemaError, match="valid_until"):
        _p(_j(d))
    assert _p(_j(answer("edit", execution="failed", dp=(0.0, 0.0, 0.045)))).edit is not None  # > 0.04 stated, <= 0.05
    with pytest.raises(SchemaError, match="norm"):
        _p(_j(answer("edit", execution="failed", dp=(0.0, 0.0, 0.051))))


def test_f1_keep_ignores_an_accompanying_edit_in_v2_only():
    d = answer(diff="keep")
    d["edit"] = {"delta_position_m": [0, 0, 0.01], "delta_rotation_rad": [0, 0, 0], "gripper": "keep",
                 "valid_until": "next_answer"}
    a = _p(_j(d), mode="F1")
    assert a.command == "continue" and a.edit is None and "keep_edit_ignored" in a.notes
    with pytest.raises(SchemaError, match="only with command edit"):
        _p(_j(d), mode="F1", version="v1")  # v1 parsing unchanged (recorded v1 runs stay reproducible)


def test_v1_ignores_the_v2_fields():
    a = _p(_j(answer("continue", segment=SEG)), version="v1")
    assert a.segment is None and a.valid_until is None
    d = answer("continue")
    d.pop("segment", None)
    assert _p(_j(d), version="v1").command == "continue"
