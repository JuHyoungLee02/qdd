import numpy as np
import pytest

from harvest.couple_joy import joy as J


def test_joystick_far_plus_x_is_xlarge_and_level():
    d = J.joystick([0.60, 0.0, 0.90], [0.40, 0.0, 0.90])
    assert d == {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "xlarge"}


def test_joystick_inside_deadband_is_none():
    d = J.joystick([0.405, 0.004, 0.906], [0.40, 0.0, 0.90])
    assert d["dir_xy"] == "none_xy" and d["dir_z"] == "none_z"


def test_joystick_diagonal_down():
    d = J.joystick([0.45, -0.05, 0.80], [0.40, 0.0, 0.90])
    assert d["dir_xy"] == "plus_x_minus_y" and d["dir_z"] == "down"


@pytest.mark.parametrize("intent,holding,released,arrived,want", [
    ({"mode": "point", "height": "above", "gripper": "keep"}, False, False, False, "approach"),
    ({"mode": "point", "height": "grasp", "gripper": "close"}, False, False, False, "descend"),
    ({"mode": "point", "height": "grasp", "gripper": "close"}, False, False, True, "close"),
    ({"mode": "gripper", "gripper": "close"}, False, False, False, "close"),
    ({"mode": "point", "height": "lift", "gripper": "keep"}, True, False, False, "lift"),
    ({"mode": "point", "height": "above", "gripper": "keep"}, True, False, False, "carry"),
    ({"mode": "point", "height": "place", "gripper": "open"}, True, False, False, "place_descend"),
    ({"mode": "point", "height": "place", "gripper": "open"}, True, False, True, "open"),
    ({"mode": "gripper", "gripper": "open"}, True, False, False, "open"),
    ({"mode": "edit", "gripper": "keep"}, False, True, False, "retreat"),
    ({"mode": "point", "height": "above", "gripper": "keep"}, False, True, False, "retreat"),
    ({"mode": "edit", "gripper": "keep"}, True, False, False, "lift"),
])
def test_vla_phase_from_planner_intent(intent, holding, released, arrived, want):
    assert J.vla_phase(intent, holding, released, arrived) == want


def test_committed_slots_and_target_by_stage():
    joy = {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "large"}
    c = J.committed("approach", joy, "o3", "o5", grip_closed_empty=False)
    assert c == {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "large", "target": "o3", "phase": "continue"}
    assert J.committed("carry", joy, "o3", "o5", False)["target"] == "o5"
    none = {"dir_xy": "none_xy", "dir_z": "none_z", "mag_coarse": "tiny"}
    assert J.committed("descend", none, "o3", "o5", False)["phase"] == "next"
    assert J.committed("approach", joy, "o3", "o5", grip_closed_empty=True)["phase"] == "hold"


def test_clamp_step_limits_every_joint_to_004():
    q = J.clamp_step(np.zeros(7), np.array([0.1, -0.1, 0.02, 0, 0, 0, 0.5]))
    assert np.allclose(q, [0.04, -0.04, 0.02, 0, 0, 0, 0.04])


def test_grip_gate_blocks_wrong_direction_and_bounds_value():
    # no gripper action allowed: hold
    assert J.grip_gate(0.10, 0.05, None, 0.107, 0.0) == 0.10
    # closing allowed: follow the VLA but never past the close target
    assert J.grip_gate(0.10, 0.05, "close", 0.107, 0.0) == 0.05
    assert J.grip_gate(0.10, 0.12, "close", 0.107, 0.0) == 0.10  # an opening move while closing is blocked
    # opening allowed, clipped to the open width
    assert J.grip_gate(0.02, 0.20, "open", 0.107, 0.0) == 0.107
