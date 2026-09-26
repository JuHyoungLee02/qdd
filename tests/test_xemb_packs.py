"""tools/xemb/packs.py (E-DIST8 add-on packs): pixel answers -> 0-1000 normalised, 'not visible' negatives, and the
equal-total rule (base rows subsampled so every arm has the same number of rows)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import packs as P  # noqa: E402

ROW = {"id": "a", "kind": "qa_xemb", "qa_kind": "ee_point_detected", "frame": "pixel", "source": "s/r",
       "prompt": "source: s/r\nframe: pixel\nCAMERAS\n- Image 1: head camera, 672x376 px; camera: unknown (no calibration).\n"
                 "Point to the right robot gripper in image 1.\nReturn JSON only.",
       "images": ["x.jpg"], "answer": json.dumps({"point": [336, 188]})}


def test_size_from_prompt():
    assert P.size_of(ROW["prompt"]) == (672, 376)


def test_point_to_n1000():
    r = P.to_n1000(ROW)
    assert json.loads(r["answer"]) == {"point": [500, 500]}
    assert "0-1000" in r["prompt"] and "not visible" in r["prompt"]
    assert r["prompt"].splitlines()[1] == "frame: pixel"


def test_trace_to_n1000():
    row = dict(ROW, qa_kind="ee_trace", answer=json.dumps({"trace": [[0, 0], [671, 375]]}))
    assert json.loads(P.to_n1000(row)["answer"]) == {"trace": [[0, 0], [999, 997]]}


def test_negative_row():
    r = P.negative(ROW, "y.jpg", "neg1")
    assert json.loads(r["answer"]) == {"visible": False} and r["images"] == ["y.jpg"]


def test_equal_total_rule():
    assert P.base_take(6521, [1300]) == 5221
    assert P.base_take(6521, [2600, 1300]) == 2621
