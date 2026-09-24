"""Pure parts of harvest.sim.planner (no Isaac): FSM transitions, oracle answers, decision points, success."""
import numpy as np
import pytest

from harvest.sim.planner import (
    FAIL_STAGE, PHASE_TIMEOUT_S, decision_points, next_phase, oracle_answer, success_from_history,
)

OK = {"on(o3,o5)": True, "holding(o3)": False, "upright(o3)": True}


def test_success_needs_one_second_continuous():
    bad = dict(OK, **{"upright(o3)": False})
    hist = [(i * 0.05, OK) for i in range(15)] + [(0.75, bad)] + [(0.8 + i * 0.05, OK) for i in range(21)]
    assert success_from_history(hist) is True
    assert success_from_history([(i * 0.05, OK) for i in range(15)]) is False


def S(**kw):
    base = dict(reached=False, t_in_phase=0.0, holding=False, lift_h=0.0, contact_under=False)
    base.update(kw)
    return base


def test_fsm_full_sequence():
    seq = [
        ("approach", S(), "approach"),
        ("approach", S(reached=True), "descend"),
        ("descend", S(), "descend"),
        ("descend", S(reached=True), "close"),
        ("close", S(t_in_phase=0.2), "close"),
        ("close", S(t_in_phase=0.8, holding=True), "lift"),
        ("lift", S(holding=True, lift_h=0.01, reached=True), "lift"),  # not high enough yet
        ("lift", S(holding=True, lift_h=0.05, reached=True), "carry"),
        ("carry", S(holding=True, reached=False), "carry"),
        ("carry", S(holding=True, reached=True), "place_descend"),
        ("place_descend", S(holding=True), "place_descend"),
        ("place_descend", S(holding=True, contact_under=True), "open"),
        ("open", S(t_in_phase=0.2), "open"),
        ("open", S(t_in_phase=0.6), "retreat"),
        ("retreat", S(reached=True), "done"),
        ("done", S(reached=True), "done"),
    ]
    for phase, sig, want in seq:
        assert next_phase(phase, sig) == want, (phase, sig)


def test_close_without_holding_is_grasp_failure():
    assert next_phase("close", S(t_in_phase=0.8, holding=False)) == "fail"
    assert FAIL_STAGE["close"] == "grasp"


def test_losing_grip_in_lift_or_carry_fails():
    assert next_phase("lift", S(holding=False, t_in_phase=0.5)) == "fail"
    assert next_phase("carry", S(holding=False, t_in_phase=0.5)) == "fail"


def test_place_descend_reaching_bottom_also_opens():
    assert next_phase("place_descend", S(holding=True, reached=True)) == "open"


def test_timeouts_fail_every_active_phase():
    for ph, lim in PHASE_TIMEOUT_S.items():
        sig = S(t_in_phase=lim + 0.01, holding=True, lift_h=0.0)
        assert next_phase(ph, sig) == "fail", ph


def test_fail_stage_names_cover_required_breakdown():
    assert set(FAIL_STAGE.values()) == {"approach_ik", "grasp", "lift", "carry", "place", "release"}


@pytest.mark.parametrize("d,want", [
    ((0.03, 0, 0), ("plus_x", "none_z", "large")),
    ((-0.01, 0, 0), ("minus_x", "none_z", "small")),
    ((0, 0.02, 0), ("plus_y", "none_z", "medium")),
    ((0.05, -0.05, 0), ("plus_x_minus_y", "none_z", "xlarge")),
    ((0, 0, -0.005), ("none_xy", "down", "tiny")),
    ((0, 0, 0.0), ("none_xy", "none_z", "tiny")),
    ((-0.004, -0.004, 0.02), ("minus_x_minus_y", "up", "medium")),
])
def test_oracle_answer_direction_and_bins(d, want):
    a = oracle_answer(np.zeros(3), np.array(d, float), 0.1, 0.1)
    assert (a["dir_xy"], a["dir_z"], a["mag_coarse"]) == want
    assert a["grip"] == "keep"


def test_oracle_answer_grip():
    assert oracle_answer(np.zeros(3), np.zeros(3), 0.107, 0.0)["grip"] == "close"
    assert oracle_answer(np.zeros(3), np.zeros(3), 0.0, 0.107)["grip"] == "open"


def test_decision_points_every_tc_from_history():
    # command moves +x at 0.1 m/s for 1 s, then closes the gripper
    hist = [(i * 0.05, np.array([0.1 * min(i * 0.05, 1.0), 0, 0]), 0.107 if i * 0.05 < 1.0 else 0.0, "approach")
            for i in range(31)]
    dps = decision_points(hist, T_c=0.33)
    assert [d[1] for d in dps] == ["ds0", "ds1", "ds2", "ds3"]
    assert [round(d[0], 2) for d in dps] == [0.0, 0.33, 0.66, 0.99]
    assert dps[0][2]["dir_xy"] == "plus_x" and dps[0][2]["mag_coarse"] == "large"  # 3.3 cm -> 4 cm bin
    assert dps[3][2]["grip"] == "close"
    assert dps[0][2]["phase"] == "approach"
