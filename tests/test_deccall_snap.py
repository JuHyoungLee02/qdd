from harvest.deccall_snap import QUESTIONS, build_snapshot_request, score


def _line(phase="carry", present=("o3", "o5", "o8"), ds="ds21"):
    return {"seed": 0, "kind": "P0", "k": 21, "ds_id": ds, "phase": phase, "text_state": "t_state: f1\nrobot: x",
            "state": {"present": list(present)},
            "oracle": {"dir_xy": "plus_y", "dir_z": "none_z", "mag_coarse": "large", "target": "o5",
                       "phase_choice": "continue", "progress": "valid_progress"}}


def test_request_has_six_questions_in_deccall_format_ne_last():
    req, oracle, shown = build_snapshot_request(_line())
    assert list(req["questions"]) == ["ds21.dir_xy", "ds21.dir_z", "ds21.mag_coarse", "ds21.target", "ds21.phase",
                                      "mon.progress"]
    assert req["state"] == "t_state: f1\nrobot: x"
    for qid, q in req["questions"].items():
        assert q["type"] == "choice"
        assert list(q["criteria"])[-1] == "NONE_ESCALATE"
    assert "stage S2" in req["questions"]["ds21.dir_xy"]["instructions"]
    assert oracle == {"ds21.dir_xy": "plus_y", "ds21.dir_z": "none_z", "ds21.mag_coarse": "large",
                      "ds21.target": "o5", "ds21.phase": "continue", "mon.progress": "valid_progress"}
    assert [q for q in QUESTIONS] == ["dir_xy", "dir_z", "mag_coarse", "target", "phase", "progress"]


def test_target_options_are_present_objects_by_number_and_stage_follows_phase():
    req, _, _ = build_snapshot_request(_line(phase="descend", present=("o10", "o3", "o5")))
    assert list(req["questions"]["ds21.target"]["criteria"]) == ["o3", "o5", "o10", "NONE_ESCALATE"]
    assert "stage S1" in req["questions"]["ds21.dir_z"]["instructions"]
    assert list(req["questions"]["ds21.phase"]["criteria"]) == ["continue", "next", "hold", "NONE_ESCALATE"]


def test_progress_shown_names_follow_r1_and_score_maps_back_to_keys():
    req, oracle, shown = build_snapshot_request(_line())
    assert list(req["questions"]["mon.progress"]["criteria"])[:3] == ["advancing", "side_change", "regressed"]
    answers = {"ds21.dir_xy": {"choice": "plus_y", "confidence": 0.6},
               "ds21.dir_z": {"choice": "NONE_ESCALATE", "confidence": 0.5},
               "ds21.mag_coarse": {"choice": "small", "confidence": 0.4},
               "ds21.target": {"choice": "o5", "confidence": 0.9},
               "ds21.phase": {"choice": "continue", "confidence": 0.7},
               "mon.progress": {"choice": "advancing", "confidence": 0.8}}
    rows = score(answers, oracle, shown)
    by = {r["question"]: r for r in rows}
    assert by["progress"]["key"] == "valid_progress" and by["progress"]["correct"]
    assert by["dir_z"]["key"] == "NONE_ESCALATE" and not by["dir_z"]["correct"] and by["dir_z"]["ne"]
    assert not by["mag_coarse"]["correct"] and by["dir_xy"]["correct"]
    assert by["target"]["p_chosen"] == 0.9


def test_missing_answer_counts_wrong():
    _, oracle, shown = build_snapshot_request(_line())
    rows = score({}, oracle, shown)
    assert len(rows) == 6 and not any(r["correct"] for r in rows) and all(r["key"] is None for r in rows)
