"""tools/xemb/src_molmoact.py (T0 pixel-only): MolmoAct trace parsing, 0-255 -> pixel, jump filter."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import src_molmoact as M  # noqa: E402


def test_parse_trace_from_answer_and_annotation():
    a = "The trajectory of the end effector is [[205,69],[150,75],[146,60]]"
    assert M.parse_trace(a) == [[205, 69], [150, 75], [146, 60]]
    assert M.parse_trace("[[142,30],[158,150]]") == [[142, 30], [158, 150]]
    assert M.parse_trace("no trace here") is None


def test_to_pixels_uses_w_minus_1_over_255():
    assert M.to_px([[255, 255], [0, 0]], 320, 240) == [[319.0, 239.0], [0.0, 0.0]]


def test_jump_filter_rejects_wild_traces():
    ok = [[100, 100], [110, 105], [120, 110], [130, 115]]
    bad = [[142, 30], [158, 150], [105, 59], [79, 79], [127, 43]]  # a real Bridge row (0-255 units)
    assert M.trace_ok(M.to_px(ok, 320, 240), 320, 240)
    assert not M.trace_ok(M.to_px(bad, 320, 240), 320, 240)


def test_record_is_pixel_frame_with_unknown_camera():
    r = M.record("molmoact/bridge", "put the fork on the left", [[10.2, 20.6], [30, 40]], 320, 240, "x.jpg", "id1")
    lines = r["prompt"].splitlines()
    assert lines[0] == "source: molmoact/bridge" and lines[1] == "frame: pixel"
    assert "camera: unknown" in r["prompt"] and "put the fork on the left" in r["prompt"]
    assert json.loads(r["answer"]) == {"trace": [[10, 21], [30, 40]]}
