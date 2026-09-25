"""E-CAM3 frame builder (tools/cam3/build_cam3.py): which other-wrist frames are needed (pure part)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "cam3"))
import build_cam3 as B  # noqa: E402


def _row(seed, k, arm="right", both=False, imgs=("cam_head", "cam_wrist_right")):
    return {"seed": seed, "k": k, "arm": arm, "bimanual": both, "images": {c: c for c in imgs}}


def test_plan_lists_the_other_wrist_of_used_single_arm_rows_only():
    rows = [_row(1, 0), _row(1, 3, "left", imgs=("cam_head", "cam_wrist_left")),
            _row(1, 6, both=True, imgs=("cam_head", "cam_wrist_right", "cam_wrist_left")),
            _row(2, 0, imgs=("cam_head",))]  # no active wrist -> not used by the baseline loader
    assert B.plan(rows) == {1: {"cam_wrist_left": [0], "cam_wrist_right": [3]}}


def test_plan_sorts_and_dedups_frames():
    rows = [_row(4, 9), _row(4, 3), _row(4, 3)]
    assert B.plan(rows) == {4: {"cam_wrist_left": [3, 9]}}
