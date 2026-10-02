"""Owner 10-02 (E-TP1 leak): the frozen hold-out definitions never become training rows; build split gate; the
robot-frame direction sentence on every slot row (main 10-02)."""
from harvest.l9 import alloc9 as AL
from harvest.l9 import specgate9 as SG
from harvest.l9 import views9 as V


def test_holdout_frozen_independent_of_definition_set():
    defs = {k: "f" for k in AL.HOLDOUT_FROZEN}
    more = dict(defs, **{f"new_def_{i}": f"fam{i % 7}" for i in range(300)})
    assert AL.holdout_defs(defs) == AL.holdout_defs(more) == sorted(AL.HOLDOUT_FROZEN)
    assert AL.holdout_defs({"x": "f"}) == []
    assert AL.is_holdout("kit_from_sink") and not AL.is_holdout("in_left_one")


def test_plan_rows_mark_holdout():
    k = AL.HOLDOUT_FROZEN[0]
    assert AL.holdout_defs({k: "f", "other": "g"}) == [k]


def test_split_leaks():
    rows = [{"task_def": "in_left_one", "ep_split": "train", "objects": ["a"], "room": "r1", "robot": "ffw_sg2"},
            {"task_def": "kit_from_sink", "ep_split": "train", "objects": ["a"], "room": "r1", "robot": "ffw_sg2"},
            {"task_def": "in_left_one", "ep_split": "holdout", "objects": ["b"], "room": "r2", "robot": "ffw_sg2"}]
    s = SG.split_leaks(rows, ood_objects={"b"}, ood_rooms={"r2"})
    assert s == {"holdout_def_rows": 1, "non_train_split_rows": 1, "ood_object_rows": 1, "ood_room_rows": 1,
                 "robot_not_gated_rows": 0}
    assert not any(SG.split_leaks(rows[:1], {"b"}, {"r2"}).values())


def test_robot_gate():
    assert AL.robot_build_ready("ffw_sg2") and AL.robot_build_ready("franka_mast")
    assert not AL.robot_build_ready("r1pro") and not AL.robot_build_ready("g1") and not AL.robot_build_ready(None)
    rows = [{"robot": "ffw_sg2"}, {"robot": "r1pro"}, {"robot": "g1"}, {"robot": "franka_mast"}]
    assert SG.split_leaks(rows)["robot_not_gated_rows"] == 2


def test_gates_split_and_frame_note():
    rows = [{"task_def": "kit_from_sink", "ep_split": "train", "prompt_path": "p", "spec_version": SG.SPEC,
             "robot": "ffw_sg2"}]
    g = SG.gates(rows, {"p": "x " + SG.FRAME_SENTENCE}, train=True, frame_note=True)
    assert g["split"]["holdout_def_rows"] == 1 and not g["ok"]
    rows[0]["task_def"] = "in_left_one"
    g = SG.gates(rows, {"p": "no sentence"}, train=True, frame_note=True)
    assert g["frame_note_missing"] == 1 and not g["ok"]
    g = SG.gates(rows, {"p": "x " + SG.FRAME_SENTENCE}, train=True, frame_note=True)
    assert g["ok"], g


def test_views_frame_note_matches_gate():
    assert V.FRAME_NOTE == SG.FRAME_SENTENCE
