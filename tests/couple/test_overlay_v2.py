"""Overlay parts of astra-couple@v2 (plan 2026-09-26 Task 18): the AxisGuide port draws the same pixels as the E-ACC
arm 'ax' (tools/eacc/arms.draw_axisguide), and drawn_elements reports what draw_overlay put on the images."""
import os
import sys

import numpy as np

from harvest.couple.overlay import CamModel, draw_axisguide, drawn_elements

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HEAD = CamModel.from_dict({"K": [[200, 0, 80], [0, 200, 60], [0, 0, 1]], "R": [[0, 0, 1], [-1, 0, 0], [0, -1, 0]],
                           "t": [0, 0, 0], "W": 160, "H": 120})


def _arms():
    sys.path.insert(0, os.path.join(ROOT, "tools", "eacc"))
    import arms  # noqa: E402
    return arms


def test_axisguide_port_is_pixel_identical_to_the_eacc_arm():
    A = _arms()
    img = np.full((120, 160, 3), 90, np.uint8)
    tip = np.array([1.0, 0.0, 0.0])
    a, ok_a = draw_axisguide(img, HEAD, tip)
    b, ok_b = A.draw_axisguide(img, HEAD, tip)
    assert ok_a and ok_b and np.array_equal(a, b) and not np.array_equal(a, img)
    c, ok = draw_axisguide(img, HEAD, np.array([-1.0, 0.0, 0.0]))  # behind the camera: nothing drawn
    assert not ok and c is img


def test_drawn_elements():
    wr = CamModel.from_dict({"K": [[20, 0, 8], [0, 20, 6], [0, 0, 1]], "R": np.eye(3).tolist(), "t": [0, 0, 0],
                             "W": 16, "H": 12})
    tip, tr = np.array([1.0, 0.0, 0.0]), [np.array([1.0, 0.0, 0.0]), np.array([1.0, 0.01, 0.0])]
    d = drawn_elements({"cam_head": HEAD, "cam_wrist_right": wr}, tip=tip, trace=tr, next_vec=np.array([0.03, 0, 0]),
                       offset_vec=np.zeros(3))
    assert d == {"head": {"ring", "axes", "next", "trace"}, "wrist": {"next"}, "axisguide": []}
    d = drawn_elements({"cam_head": HEAD}, tip=np.array([-1.0, 0, 0]), trace=[], next_vec=None,
                       offset_vec=np.array([0, 0, 0.01]), axisguide=["cam_head"])
    assert d == {"head": set(), "wrist": None, "axisguide": ["cam_head"]}
    assert drawn_elements({}, tip=tip, trace=tr) is None
