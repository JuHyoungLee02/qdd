"""tools/xemb/build_open8.py + src_refspatial.py: E-OPEN8 row checks (header, missing image, answer leak) and the
RefSpatial point parser."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import build_open8 as B  # noqa: E402
from xemb import src_refspatial as RS  # noqa: E402


def _row(tmp_path, answer, kind="control_xemb", header=True):
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")
    p = ("source: s/r\nframe: base_r\n" if header else "hello\n") + "..."
    return {"kind": kind, "prompt": p, "images": [str(img)], "answer": answer, "frame": "base_r"}


def test_row_ok_accepts_clean_control(tmp_path):
    a = json.dumps({"assessment": {}, "command": {"mode": "eef", "position_m": [0.4, 0, 1.0], "gripper": "keep"}})
    assert B.row_ok(_row(tmp_path, a)) == (True, "")


def test_row_ok_rejects_leak_header_and_missing_image(tmp_path):
    a = json.dumps({"command": {"mode": "eef", "position_m": [0.4, 0, 1.0]}, "frame": "pixel"})
    assert B.row_ok(_row(tmp_path, a)) == (False, "foreign_key_in_answer")
    ok = json.dumps({"command": {"mode": "stop"}})
    assert B.row_ok(_row(tmp_path, ok, header=False)) == (False, "no_source_frame_header")
    r = _row(tmp_path, ok)
    r["images"] = [str(tmp_path / "nope.jpg")]
    assert B.row_ok(r) == (False, "missing_image")


def test_refspatial_points():
    assert RS.points("[(0.613, 0.404), (0.5, 0.25)]") == [(0.613, 0.404), (0.5, 0.25)]
    assert RS.points("(A) yes") == []
