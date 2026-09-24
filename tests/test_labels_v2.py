import math

import numpy as np
import pytest

from harvest.e3lite import state_text
from harvest.labels_v2 import (MAG_EDGES_M, code_rule_v2, delta, dir_xy_label, dir_z_label, goal_point, labels,
                               mag_label, motion_phase, phase_label)

S1_TXT = ("t_state: f0 (t=0.00s)  contract: c1  stage: S1 \"pick up mug o3\"\nrobot: gripper=open arm=still\n"
          "objects:\n  o3 mug red | on(table) | upright\n  o5 tray blue | on(table) | upright\n"
          "facts: gripper_open=yes holding(o3)=no lifted(o3)=no upright(o3)=yes upright(o5)=yes\n"
          "stage S1: exit=holding(o3) lifted(o3) invariants= elapsed=normal\nchanges (last 3s): ")
S2_TXT = ("t_state: f0 (t=0.00s)  contract: c1  stage: S2 \"place mug o3 on tray o5\"\n"
          "robot: gripper=closed_holding(o3) arm=moving\nobjects:\n  o3 mug red | held_by_gripper | upright\n"
          "  o5 tray blue | on(table) | upright\n"
          "facts: gripper_open=no holding(o3)=yes on(o3,o5)=no upright(o3)=yes upright(o5)=yes\n"
          "stage S2: exit=on(o3,o5) invariants=holding(o3) elapsed=normal\nchanges (last 3s): ")
S1_HOLD = S1_TXT.replace("gripper=open", "gripper=closed_holding(o3)").replace(
    "gripper_open=yes holding(o3)=no", "gripper_open=no holding(o3)=yes")
MUG, TRAY = (0.428, -0.382, 0.0475), (0.477, -0.174, 0.0075)


def _line(grip, phase="approach", o3=MUG, o5=TRAY, gopen=True, hold=False, lifted=False, on=False, text=S1_TXT):
    pred = {"gripper_open": gopen, "holding(o3)": hold, "lifted(o3)": lifted, "on(o3,o5)": on}
    objs = {"o3": {"pos": list(o3), "he": [0.032, 0.032, 0.0475]}, "o5": {"pos": list(o5), "he": [0.09, 0.07, 0.0075]}}
    return {"seed": 0, "kind": "P0", "k": 0, "ds_id": "ds0", "phase": phase, "text_state": text, "pred": pred,
            "state": {"present": ["o3", "o5"], "obs": {"pred": pred, "raw": {"objs": objs, "grip": {"pos": list(grip)}}}},
            "oracle": {"dir_xy": "plus_x", "dir_z": "down", "mag_coarse": "xlarge", "target": "o3",
                       "phase_choice": "continue", "progress": "valid_progress"}}


def test_mag_edges_are_geometric_midpoints():
    assert MAG_EDGES_M == pytest.approx([math.sqrt(0.005 * 0.01), math.sqrt(0.01 * 0.02), math.sqrt(0.02 * 0.04),
                                         math.sqrt(0.04 * 0.08)])
    assert mag_label(np.zeros(3)) == "tiny" and mag_label([0.007, 0, 0]) == "tiny"
    assert mag_label([0.0071, 0, 0]) == "small" and mag_label([0, 0.0142, 0]) == "medium"
    assert mag_label([0, 0, -0.0283]) == "large" and mag_label([0.05, 0.03, 0]) == "xlarge"


def test_dir_labels_sign_pattern_with_1cm_deadband():
    assert dir_xy_label([0.009, -0.009, 0]) == "none_xy"
    assert dir_xy_label([0.20, -0.011, 0]) == "plus_x_minus_y"  # sign pattern, not angle quantization
    assert dir_xy_label([-0.02, 0.005, 0]) == "minus_x" and dir_xy_label([0.0, 0.01, 0]) == "plus_y"
    assert dir_z_label([0, 0, -0.0099]) == "none_z" and dir_z_label([0, 0, 0.01]) == "up"
    assert dir_z_label([0, 0, -0.3]) == "down"


def test_approach_goal_is_10cm_above_mug_top_from_actual_pose():
    ln = _line(grip=(0.334, -0.248, 0.244))
    assert motion_phase(ln) == "approach"
    assert goal_point("approach", ln["state"]) == pytest.approx([0.428, -0.382, 0.0475 + 0.0475 + 0.10])
    m, d = delta(ln)
    assert m == "approach" and d == pytest.approx([0.094, -0.134, 0.195 - 0.244])


def test_grasp_when_aligned_then_next_at_goal():
    ln = _line(grip=(0.430, -0.380, 0.20))  # 2.8 mm off in xy -> aligned
    assert motion_phase(ln) == "grasp"
    lab = labels(ln)
    assert lab["dir_xy"] == "none_xy" and lab["dir_z"] == "down" and lab["phase_choice"] == "continue"
    ln = _line(grip=(0.428, -0.382, 0.0475 + 0.0295 + 0.004))
    lab = labels(ln)
    assert lab["dir_z"] == "none_z" and lab["mag_coarse"] == "tiny" and lab["phase_choice"] == "next"
    assert lab["target"] == "o3"


def test_lift_targets_mug_and_goes_to_carry_height_next_when_lifted():
    ln = _line(grip=(0.43, -0.38, 0.08), phase="lift", o3=(0.43, -0.38, 0.05), gopen=False, hold=True)
    lab = labels(ln)
    assert lab["motion_phase"] == "lift" and lab["dir_xy"] == "none_xy" and lab["dir_z"] == "up"
    assert lab["target"] == "o3" and lab["phase_choice"] == "continue"
    ln = _line(grip=(0.43, -0.38, 0.12), phase="lift", o3=(0.43, -0.38, 0.09), gopen=False, hold=True, lifted=True)
    assert labels(ln)["phase_choice"] == "next"  # S1 exit holding(o3) and lifted(o3)


def test_carry_then_place_in_s2():
    ln = _line(grip=(0.40, -0.38, 0.18), phase="carry", o3=(0.40, -0.38, 0.15), gopen=False, hold=True, text=S2_TXT)
    lab = labels(ln)
    assert lab["motion_phase"] == "carry" and lab["dir_xy"] == "plus_x_plus_y" and lab["dir_z"] == "up"
    assert lab["target"] == "o5"
    ln = _line(grip=(0.477, -0.174, 0.20), phase="place_descend", o3=(0.477, -0.174, 0.17), gopen=False, hold=True,
               text=S2_TXT)
    m, d = delta(ln)
    # mug bottom 0.1225 above the tray top 0.015 -> down 0.1075 - 0.003
    assert m == "place" and d == pytest.approx([0, 0, -(0.1225 - 0.015) + 0.003])


def test_retreat_wait_and_hold_rules():
    ln = _line(grip=(0.477, -0.174, 0.10), phase="retreat", o3=(0.477, -0.174, 0.0625), on=True,
               text=S2_TXT.replace("closed_holding(o3)", "open"))
    lab = labels(ln)
    assert lab["motion_phase"] == "retreat" and lab["dir_z"] == "up" and lab["phase_choice"] == "next"
    ln = _line(grip=(0.428, -0.382, 0.08), phase="close", gopen=False, hold=False)
    lab = labels(ln)
    assert lab["motion_phase"] == "wait" and lab["mag_coarse"] == "tiny" and lab["phase_choice"] == "hold"
    ln = _line(grip=(0.40, -0.30, 0.10), phase="retreat", on=False, text=S2_TXT)
    assert phase_label("S2", "open", {"holding(o3)": False, "on(o3,o5)": False}, np.array([0, 0, 0.1])) == "hold"


def test_progress_is_the_old_oracle_value():
    ln = _line(grip=(0.334, -0.248, 0.244))
    ln["oracle"]["progress"] = "allowed_change"
    assert labels(ln)["progress"] == "allowed_change"


@pytest.mark.parametrize("grip,phase,kw", [
    ((0.334, -0.248, 0.244), "approach", {}),
    ((0.40, -0.38, 0.18), "carry", dict(o3=(0.40, -0.38, 0.15), gopen=False, hold=True, text=S2_TXT)),
    ((0.43, -0.38, 0.08), "lift", dict(o3=(0.43, -0.38, 0.05), gopen=False, hold=True, text=S1_HOLD)),
])
def test_code_rule_from_s1_text_reproduces_labels_away_from_edges(grip, phase, kw):
    ln = _line(grip=grip, phase=phase, **kw)
    lab, rule = labels(ln), code_rule_v2(state_text(ln, "S1"))
    for q in ("dir_xy", "dir_z", "mag_coarse", "target", "phase_choice", "progress"):
        if q != "progress":
            assert rule[q] == lab[q], q
    assert rule["motion_phase"] == lab["motion_phase"]


def test_code_rule_reads_fine_serializer():
    ln = _line(grip=(0.428, -0.382, 0.0475 + 0.0295 + 0.012))  # 12 mm above the grasp point
    fine = state_text(ln, "S1", step_cm=0.5)
    assert "dz=-4.0" in fine  # o3 centre - gripper = -4.15 cm -> 0.5 cm grid
    assert code_rule_v2(fine)["dir_z"] == labels(ln)["dir_z"] == "down"
