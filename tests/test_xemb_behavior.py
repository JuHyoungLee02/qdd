"""tools/xemb/src_behavior.py pure parts: task_info layout, depth dequantisation, seg palette (BEHAVIOR v3.7.2)."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import src_behavior as B  # noqa: E402

KEYS = ["agent.n.01_1_real", "agent.n.01_1_pos", "agent.n.01_1_ori_cos", "agent.n.01_1_ori_sin",
        "radio_receiver.n.01_1_real", "radio_receiver.n.01_1_pos", "radio_receiver.n.01_1_ori_cos",
        "radio_receiver.n.01_1_ori_sin", "radio_receiver.n.01_1_in_gripper_left",
        "radio_receiver.n.01_1_in_gripper_right", "table.n.02_1_real", "table.n.02_1_pos"]


def test_task_layout_offsets_match_the_46d_vector():
    lay = B.task_layout(KEYS)
    assert lay["agent.n.01_1"]["pos"] == slice(1, 4)
    assert lay["radio_receiver.n.01_1"]["pos"] == slice(11, 14)  # radio (3.366, 5.919, 0.534) in episode 10
    assert lay["radio_receiver.n.01_1"]["in_gripper_right"] == slice(21, 22)
    assert lay["table.n.02_1"]["pos"] == slice(23, 26)


def test_dequantize_endpoints_and_monotone():
    q = np.array([0, 8000, 16383])
    d = B.dequantize(q)
    assert d[0] == pytest.approx(0.0, abs=1e-9) and d[2] == pytest.approx(10.0, abs=1e-6)
    assert d[0] < d[1] < d[2]


def test_palette_first_colours():
    p = B.yuv_palette(74)  # 74 ids -> 5 levels per channel
    assert p.shape == (74, 3)
    assert p[0].tolist() == [16, 16, 16]
    assert p[25].tolist() == [70, 16, 16]  # linspace(16, 235, 5)[1] = 70.75 -> uint8 70
