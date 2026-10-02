"""4-slot camera schema (views9): fixed slot order, slot dropout, arm in the command, parse back."""
import json
import os
from collections import Counter

import numpy as np

from harvest.l9 import views9 as V

FX = os.path.join(os.path.dirname(__file__), "fixtures")
CAM = {"W": 424, "H": 240, "fx": 200.0, "fy": 200.0, "cx": 212.0, "cy": 120.0,
       "R": [[0, -1, 0], [-1, 0, 0], [0, 0, -1.0]], "t": [0.3, 0.2, 1.2]}
ANS = json.dumps({"assessment": {"evidence_view": "both"}, "command": {"mode": "point", "point_2d": [500, 500]}})


def _text():
    return open(os.path.join(FX, "l9_v2_1.txt"), encoding="utf-8").read()


def test_all_slots_listed_in_order_and_parse():
    r = V.canonical(_text(), ANS, "right", "h.png", ("w.png", CAM), ("o.png", CAM), ("t.png", CAM),
                    np.random.default_rng(0), wrist_keep=1.0)
    assert r["image_views"] == ["head", "wrist_left", "wrist_right", "third_person"]
    assert r["images"] == ["h.png", "o.png", "w.png", "t.png"]
    assert V.parse_slots(r["text"]) == {"head": 1, "wrist_left": 2, "wrist_right": 3, "third_person": 4}
    assert "RIGHT wrist camera (image 3)" in r["text"] or "Right wrist camera (image 3)" in r["text"]
    assert json.loads(r["answer"])["command"]["arm"] == "right"
    assert V.POINT_NOTE in r["text"] and not [x for x in r["text"].split("\n") if x.startswith("- Image 2:")]


def test_dropout_head_only_and_left_arm():
    r = V.canonical(_text(), ANS, "left", "h.png", ("w.png", CAM), None, None, np.random.default_rng(0),
                    wrist_keep=0.0)
    assert r["images"] == ["h.png"] and r["image_views"] == ["head"]
    assert V.parse_slots(r["text"]) == {"head": 1, "wrist_left": None, "wrist_right": None, "third_person": None}
    a = json.loads(r["answer"])
    assert a["command"]["arm"] == "left" and a["assessment"]["evidence_view"] == "head"
    assert "wrist camera (image 2)" not in r["text"] and "The wrist image has no drawing" not in r["text"]


def test_slot_histogram_has_1_2_3_image_rows():
    h = Counter()
    for i in range(300):
        r = V.canonical(_text(), ANS, "right", "h.png", ("w.png", CAM), ("o.png", CAM), None, V.row_rng(f"r{i}"))
        V.parse_slots(r["text"])
        assert r["image_views"][0] == "head"
        h[len(r["images"])] += 1
    assert set(h) == {1, 2, 3} and 0.4 < h[3] / 300 < 0.6


def test_row_rng_is_stable():
    assert V.row_rng("x", 1).random() == V.row_rng("x", 1).random()


def test_slot_line_units():
    s = V.slot_line("wrist_left", CAM, "l9/ffw_sg2")
    assert s.startswith("camera: wrist_left,") and "m above the floor" in s and "deg down" in s and "hfov" in s
