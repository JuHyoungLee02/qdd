"""tools/xemb/steps.py: gripper-event segmentation of a public episode into our step vocabulary
(above_target -> descend_close -> carry_up -> carry_over -> lower_open -> retreat, recovery 'reopen')."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import steps as S  # noqa: E402


def _line(a, b, n):
    return np.linspace(a, b, n, endpoint=False)


def _pick_place(empty_first=False):
    """Synthetic 10 Hz pick-and-place in a base frame; returns ee (N,3), closed (N,), held (N,)."""
    P = []
    closed, held = [], []

    def seg(a, b, n, c, h):
        P.extend(_line(a, b, n))
        closed.extend([c] * n)
        held.extend([h] * n)

    start, above, grasp = [0.30, 0.0, 0.30], [0.50, 0.10, 0.25], [0.50, 0.10, 0.10]
    if empty_first:
        wrong = [0.53, 0.13, 0.10]
        seg(start, [0.53, 0.13, 0.25], 10, False, False)
        seg([0.53, 0.13, 0.25], wrong, 8, False, False)
        seg(wrong, wrong, 4, True, False)  # empty close
        seg(wrong, [0.53, 0.13, 0.25], 6, False, False)  # reopen + lift
        start = [0.53, 0.13, 0.25]
    seg(start, above, 10, False, False)
    seg(above, grasp, 8, False, False)
    seg(grasp, grasp, 3, True, True)  # closing
    seg(grasp, [0.50, 0.10, 0.25], 8, True, True)
    seg([0.50, 0.10, 0.25], [0.40, -0.20, 0.25], 12, True, True)
    seg([0.40, -0.20, 0.25], [0.40, -0.20, 0.12], 8, True, True)
    seg([0.40, -0.20, 0.12], [0.40, -0.20, 0.12], 2, False, False)  # open
    seg([0.40, -0.20, 0.12], [0.40, -0.20, 0.25], 8, False, False)
    seg([0.40, -0.20, 0.25], [0.40, -0.20, 0.25], 5, False, False)
    return np.array(P), np.array(closed), np.array(held)


def test_events_from_opening_with_hysteresis():
    a = np.array([1, 1, 0.95, 0.7, 0.4, 0.4, 0.45, 0.85, 0.95, 1.0])
    closed = S.closed_from_opening(a, close_below=0.8, open_above=0.9)
    assert closed.tolist() == [False, False, False, True, True, True, True, True, False, False]


def test_clean_pick_place_yields_the_six_steps_in_order():
    ee, closed, held = _pick_place()
    segs = S.segment(ee, closed, held)
    assert [s["step"] for s in segs] == ["above_target", "descend_close", "carry_up", "carry_over", "lower_open",
                                         "retreat", "done"]
    by = {s["step"]: s for s in segs}
    assert np.allclose(by["descend_close"]["target"], [0.50, 0.10, 0.10], atol=0.02)
    assert by["descend_close"]["gripper"] == "close"
    assert by["above_target"]["target"][2] > by["descend_close"]["target"][2] + 0.05
    assert by["lower_open"]["gripper"] == "open"
    assert np.allclose(by["lower_open"]["target"], [0.40, -0.20, 0.12], atol=0.02)
    assert by["carry_over"]["target"][2] > 0.2
    assert by["done"]["gripper"] is None
    # segments tile the time axis without overlap
    for a, b in zip(segs, segs[1:]):
        assert a["t1"] == b["t0"]


def test_empty_close_gives_reopen_and_drops_the_failed_approach():
    ee, closed, held = _pick_place(empty_first=True)
    segs = S.segment(ee, closed, held)
    steps = [s["step"] for s in segs]
    assert steps[0] == "reopen"
    assert steps[1:] == ["above_target", "descend_close", "carry_up", "carry_over", "lower_open", "retreat", "done"]
    assert segs[0]["gripper"] == "open" and segs[0]["target"] is None


def test_no_held_signal_assumes_every_close_holds():
    ee, closed, _ = _pick_place()
    segs = S.segment(ee, closed, None)
    assert "descend_close" in [s["step"] for s in segs]


def test_drop_during_carry_ends_the_cycle_without_place_labels():
    ee, closed, held = _pick_place()
    i = int(np.nonzero(closed)[0][0]) + 15
    held[i:] = False  # object slips while the gripper stays closed
    segs = S.segment(ee, closed, held)
    steps = [s["step"] for s in segs]
    assert "lower_open" not in steps and "carry_over" not in steps
    assert steps[:3] == ["above_target", "descend_close", "carry_up"] or steps[:2] == ["above_target", "descend_close"]


def test_sample_frames_are_inside_their_segment():
    ee, closed, held = _pick_place()
    segs = S.segment(ee, closed, held)
    for s in segs:
        for k in S.sample_frames(s, n=2):
            assert s["t0"] <= k < s["t1"]
