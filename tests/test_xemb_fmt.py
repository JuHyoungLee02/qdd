"""tools/xemb/fmt.py + gates.py: robot self-info block, perception QA and frame-explicit control (C') records,
the frame-leak checker, and the quality gates."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from xemb import fmt as F  # noqa: E402
from xemb import gates as Q  # noqa: E402

ROBOT = {
    "name": "rby1", "source": "molmobot/rby1", "arm": "right", "desc": "Rainbow RB-Y1 wheeled humanoid (simulation)",
    "gripper": {"open_gap_m": 0.10, "approach_local": "+z"},
    "workspace": {"x": [0.25, 0.75], "y": [-0.6, 0.2], "z": [0.7, 1.4]},
    "cameras": [
        {"name": "head camera", "W": 1024, "H": 576, "K": [[109.2, 0, 512], [0, 109.2, 288], [0, 0, 1]],
         "T_base_cam": np.eye(4).tolist()},
        {"name": "right wrist camera", "W": 1024, "H": 576, "K": [[500.0, 0, 512], [0, 500, 288], [0, 0, 1]],
         "T_base_cam": None},
    ],
}


def test_self_info_block_starts_with_source_and_frame_and_lists_intrinsics():
    t = F.self_info(ROBOT)
    lines = t.splitlines()
    assert lines[0] == "source: molmobot/rby1"
    assert lines[1] == "frame: base_rby1"
    assert "fx 109.2" in t and "1024x576" in t
    assert "x 0.25..0.75" in t
    assert "moves with the hand" in t  # wrist camera without a fixed pose


def test_our_answer_spec_is_the_runtime_one():
    from harvest.astra_solo import prompts as PR
    assert F.ANSWER == PR.ANSWER


def test_control_record_answer_passes_our_runtime_schema_and_uses_the_segment_target():
    from harvest.astra_solo.schema import validate
    seg = {"step": "descend_close", "t0": 3, "t1": 9, "target": [0.51, -0.12, 0.93], "target_t": 9, "gripper": "close"}
    rec = F.control_record(ROBOT, seg, k=4, tcp=[0.5, -0.1, 1.0], opening_m=0.1, task="Pick up the mug and put it in "
                           "the bowl", tgt="mug", place="bowl", history=["1: eef to (0.500, -0.100, 1.050), gripper keep"],
                           first=False, images=["h.jpg", "w.jpg"], rid="x")
    parsed, err = validate(rec["answer"])
    assert not err
    assert parsed["command"]["mode"] == "eef" and parsed["command"]["gripper"] == "close"
    assert np.allclose(parsed["command"]["position_m"], [0.51, -0.12, 0.93])
    assert rec["prompt"].startswith("source: molmobot/rby1\nframe: base_rby1")
    assert "frame" not in json.loads(rec["answer"])  # the tag lives in the request only (leak test relies on this)


def test_control_record_reopen_and_done():
    from harvest.astra_solo.schema import validate
    for seg, mode in (({"step": "reopen", "t0": 0, "t1": 3, "target": None, "target_t": None, "gripper": "open"},
                       "gripper"),
                      ({"step": "done", "t0": 0, "t1": 3, "target": None, "target_t": None, "gripper": None}, "stop")):
        rec = F.control_record(ROBOT, seg, k=1, tcp=[0.5, -0.1, 1.0], opening_m=0.02, task="t", tgt="mug",
                               place="bowl", history=[], first=False, images=["h.jpg"], rid="y")
        parsed, err = validate(rec["answer"])
        assert not err and parsed["command"]["mode"] == mode


def test_perception_records_are_pixel_or_camera_tagged():
    r = F.qa_point(ROBOT, "ee_point", [100.4, 200.6], cam=0, image="h.jpg", rid="a")
    assert r["prompt"].splitlines()[1] == "frame: pixel"
    assert json.loads(r["answer"]) == {"point": [100, 201]}
    r = F.qa_xyz(ROBOT, "obj_center_cam", [0.1234, -0.2, 1.5], cam=0, image="h.jpg", rid="b", name="radio")
    assert r["prompt"].splitlines()[1] == "frame: cam_head"
    assert json.loads(r["answer"]) == {"xyz_cam": [0.123, -0.2, 1.5]}


def test_leak_checker_flags_foreign_keys_and_out_of_box_targets():
    ours = {"x": [0.25, 0.65], "y": [-0.5, 0.1], "z": [0.875, 1.25]}
    ok = json.dumps({"assessment": {}, "command": {"mode": "eef", "position_m": [0.4, -0.2, 1.0], "gripper": "keep"}})
    assert F.leak_flags(ok, ours) == []
    bad = json.dumps({"command": {"mode": "eef", "position_m": [3.4, 5.2, 1.0], "gripper": "keep"}, "frame": "pixel"})
    fl = F.leak_flags(bad, ours)
    assert "foreign_key:frame" in fl and "outside_box" in fl


def test_gate_point_on_reference_points():
    ref = np.array([[100, 100], [120, 100], [110, 130], [np.nan, np.nan]])
    assert Q.on_points([110, 110], ref, margin_px=10)
    assert not Q.on_points([200, 200], ref, margin_px=10)


def test_gate_near_points_tolerates_tip_beyond_body_points():
    ref = np.array([[100, 100], [120, 100], [110, 130]])  # diag ~ 36 px
    assert Q.near_points([110, 145], ref, k=0.5)  # 15 px past the body points
    assert not Q.near_points([110, 200], ref, k=0.5)


def test_gate_point_on_mask():
    m = np.zeros((50, 50), bool)
    m[20:30, 20:30] = True
    assert Q.on_mask([25, 25], m, r_px=0)
    assert Q.on_mask([32, 25], m, r_px=3)
    assert not Q.on_mask([40, 40], m, r_px=3)


def test_summary_rates():
    s = Q.rate([True, True, False, True])
    assert s == {"n": 4, "pass": 3, "rate": 0.75}
