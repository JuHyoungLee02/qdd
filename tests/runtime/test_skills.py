"""Executor S (runtime/skills.py): decisions -> bounded motion and gripper events."""
import numpy as np
import pytest

from harvest.runtime.skills import (MAG_CAP, PickPlaceSkill, apply_residual, constraint, project,
                                    residual_hook_zero)

TZ = 0.85  # table top z (world)


def _raw(g, mug=(0.40, -0.20, 0.0475), tray=(0.45, -0.05, 0.0075)):
    return {"grip": {"pos": list(g), "w": 0.107},
            "objs": {"o3": {"pos": list(mug), "he": [0.032, 0.032, 0.0475]},
                     "o5": {"pos": list(tray), "he": [0.09, 0.07, 0.0075]}}}


OPEN = {"gripper_open": True, "holding(o3)": False, "lifted(o3)": False}
HOLD = {"gripper_open": False, "holding(o3)": True, "lifted(o3)": False}
DEC = {"dir_xy": "plus_x_minus_y", "dir_z": "down", "mag_coarse": "xlarge", "target": "o3", "phase": "continue"}


def _skill(g=(0.30, -0.10, 0.25)):
    s = PickPlaceSkill(dt=0.01)
    tcp = np.array(g) + [0, 0, TZ]  # TCP = finger mid in this fake
    s.reset(0.0, tcp, [np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4)])
    return s, tcp


def test_constraint_and_projection():
    signs, cap = constraint(DEC)
    assert signs == (1, -1, -1) and cap == np.inf
    assert constraint({**DEC, "phase": "hold"}) is None
    assert constraint({**DEC, "dir_xy": None}) is None
    assert constraint({**DEC, "mag_coarse": "small"})[1] == pytest.approx(MAG_CAP["small"])
    np.testing.assert_allclose(project([0.05, 0.02, -0.004], (1, -1, 0)), [0.05, 0.0, -0.004])  # y disagrees
    np.testing.assert_allclose(project([0.05, 0.0, -0.03], (1, 0, 0)), [0.05, 0.0, 0.0])  # z outside dead band


def test_tick_moves_toward_subgoal_at_speed_only_with_agreeing_decision():
    s, tcp = _skill()
    s.begin_slot(0, DEC)
    c = s.tick(0.0, _raw((0.30, -0.10, 0.25)), OPEN, tcp, TZ)
    assert c.allowed and c.motion == "approach"
    step = c.pos_w - tcp
    assert np.linalg.norm(step) == pytest.approx(0.20 * 0.01, rel=1e-6)
    assert step[0] > 0 and step[1] < 0 and step[2] < 0


def test_no_motion_on_hold_missing_or_target_mismatch():
    for dec in ({**DEC, "phase": "hold"}, {}, {**DEC, "target": "o5"}, {**DEC, "dir_z": "NONE_ESCALATE"}):
        s, tcp = _skill()
        s.begin_slot(0, dec)
        c = s.tick(0.0, _raw((0.30, -0.10, 0.25)), OPEN, tcp, TZ)
        np.testing.assert_allclose(c.pos_w, tcp)
        assert not c.allowed


def test_mag_bin_caps_travel_per_step():
    s, tcp = _skill()
    s.begin_slot(0, {**DEC, "mag_coarse": "tiny"})
    for i in range(33):
        c = s.tick(i * 0.01, _raw((0.30, -0.10, 0.25)), OPEN, tcp, TZ)
    assert np.linalg.norm(c.pos_w - tcp) == pytest.approx(MAG_CAP["tiny"], rel=1e-6)


def test_close_needs_next_and_reached_then_lift_or_contradict():
    g_grasp = (0.40, -0.20, 0.0475 + 0.0475 - 0.018)  # pad centre 1.8 cm below the mug top, aligned
    tcp = np.array(g_grasp) + [0, 0, TZ]
    s = PickPlaceSkill(dt=0.01)
    s.reset(0.0, tcp, [1, 0, 0, 0])
    s.begin_slot(0, {**DEC, "dir_xy": "none_xy", "dir_z": "none_z", "phase": "continue"})
    s.tick(0.0, _raw(g_grasp), OPEN, tcp, TZ)
    assert s.phase == "descend" and s.cmd_w == pytest.approx(0.107)
    s.begin_slot(1, {**DEC, "dir_xy": "none_xy", "dir_z": "none_z", "phase": "next"})
    s.tick(0.33, _raw(g_grasp), OPEN, tcp, TZ)
    assert s.phase == "close" and s.cmd_w == pytest.approx(0.05)
    assert s.irreversible("phase", "next") is False  # already closing
    s.tick(0.95, _raw(g_grasp), HOLD, tcp, TZ)
    assert s.phase == "lift"
    # a miss: expected_after holding(o3) false -> CONTRADICT for this step, gripper reopens
    s2 = PickPlaceSkill(dt=0.01)
    s2.reset(0.0, tcp, [1, 0, 0, 0])
    s2.begin_slot(1, {**DEC, "dir_xy": "none_xy", "dir_z": "none_z", "phase": "next"})
    s2.tick(0.33, _raw(g_grasp), OPEN, tcp, TZ)
    s2.tick(0.95, _raw(g_grasp), {"gripper_open": False, "holding(o3)": False}, tcp, TZ)
    assert s2.phase == "approach" and s2.cmd_w == pytest.approx(0.107)
    assert s2.step_outcome(tcp)[0] == "CONTRADICT"


def _holding_skill():
    g_grasp = (0.40, -0.20, 0.0475 + 0.0475 - 0.018)
    tcp = np.array(g_grasp) + [0, 0, TZ]
    s = PickPlaceSkill(dt=0.01)
    s.reset(0.0, tcp, [1, 0, 0, 0])
    s.begin_slot(1, {**DEC, "dir_xy": "none_xy", "dir_z": "none_z", "phase": "next"})
    s.tick(0.33, _raw(g_grasp), OPEN, tcp, TZ)
    for i in range(62):  # close wait (0.6 s) with the mug held
        s.tick(0.34 + 0.01 * i, _raw(g_grasp), HOLD, tcp, TZ)
    assert s.phase == "lift"
    return s, g_grasp, tcp


def test_one_tick_holding_dropout_is_not_an_object_loss():
    """Pre-R7 fix (R6 issue 6, DEV seed 1, trace in pre_r7_fixes.md): the gripper applied torque drops to ~0 for one
    100 Hz tick while the pads still touch the mug (width 75 mm, contacts on); a single-sample `holding` = false made
    the skill re-open and drop the mug. The planner debounces holding (HOLD_DEBOUNCE 0.15 s) -> so does S."""
    s, g, tcp = _holding_skill()
    t0 = 0.97
    EMPTY = {"gripper_open": False, "holding(o3)": False}
    s.tick(t0, _raw(g), EMPTY, tcp, TZ)  # one-tick dropout
    s.tick(t0 + 0.01, _raw(g), HOLD, tcp, TZ)
    assert s.phase == "lift" and s.retries == 0 and s.cmd_w < 0.107
    for i in range(20):  # a real loss (0.2 s of closed-empty) is still caught
        s.tick(t0 + 0.02 + 0.01 * i, _raw(g), EMPTY, tcp, TZ)
    assert s.phase == "approach" and s.retries == 1 and s.cmd_w == pytest.approx(0.107)


def test_stage_switch_needs_next_and_exit_predicates():
    g = (0.40, -0.20, 0.12)
    tcp = np.array(g) + [0, 0, TZ]
    s = PickPlaceSkill(dt=0.01)
    s.reset(0.0, tcp, [1, 0, 0, 0])
    s.begin_slot(0, {**DEC, "dir_xy": "none_xy", "dir_z": "up", "phase": "continue"})
    s.tick(0.0, _raw(g, mug=(0.40, -0.20, 0.12 - 0.03)), {**HOLD, "lifted(o3)": True}, tcp, TZ)
    assert s.stage == "S1" and s.phase == "lift"
    s.begin_slot(1, {**DEC, "dir_xy": "none_xy", "dir_z": "up", "phase": "next"})
    s.tick(0.33, _raw(g, mug=(0.40, -0.20, 0.12 - 0.03)), {**HOLD, "lifted(o3)": True}, tcp, TZ)
    assert s.stage == "S2" and s.phase == "carry"


def _lifted_skill_with_bias():
    g = (0.40, -0.20, 0.12)
    tcp = np.array(g) + [0, 0, TZ]
    s = PickPlaceSkill(dt=0.01)
    s.reset(0.0, tcp, [1, 0, 0, 0])
    s.nudge([0.0, 0.02, 0.0, 0.0, 0.0, 0.0], TZ)  # an Astra offset applied during S1 (pick)
    return s, g, tcp


def test_bias_is_cleared_at_the_s1_to_s2_stage_change():
    """Task 19 fix 2 (ruling F19b): a pick-time correction must not shift the place sub-goal -- the bias is cleared
    (and logged) when the stage switches S1 -> S2; phase changes inside a stage keep it."""
    s, g, tcp = _lifted_skill_with_bias()
    raw, pred = _raw(g, mug=(0.40, -0.20, 0.12 - 0.03)), {**HOLD, "lifted(o3)": True}
    s.begin_slot(0, {**DEC, "dir_xy": "none_xy", "dir_z": "up", "phase": "continue"})
    s.tick(0.0, raw, pred, tcp, TZ)
    assert s.phase == "lift" and s.bias[1] == pytest.approx(0.02)  # phase change inside S1 keeps it
    s.begin_slot(1, {**DEC, "dir_xy": "none_xy", "dir_z": "up", "phase": "next"})
    ev = s.tick(0.33, raw, pred, tcp, TZ).events
    assert s.stage == "S2" and np.all(s.bias == 0.0)
    clr = [e for e in ev if e.get("event") == "bias_cleared"]
    assert len(clr) == 1 and clr[0]["why"] == "stage_S2" and clr[0]["bias"] == [0.0, 0.02, 0.0]
    # the place sub-goal is unshifted: the next S2 tick moves exactly like a skill that never had a bias
    ref = PickPlaceSkill(dt=0.01)
    ref.reset(0.0, tcp, [1, 0, 0, 0])
    ref.begin_slot(0, {**DEC, "dir_xy": "none_xy", "dir_z": "up", "phase": "continue"})
    ref.tick(0.0, raw, pred, tcp, TZ)
    ref.begin_slot(1, {**DEC, "dir_xy": "none_xy", "dir_z": "up", "phase": "next"})
    ref.tick(0.33, raw, pred, tcp, TZ)
    carry = {**DEC, "dir_xy": "plus_x_plus_y", "dir_z": "none_z", "phase": "continue", "target": "o5"}
    for sk in (s, ref):
        sk.cmd_pos = tcp.copy()
        sk.begin_slot(2, carry)
    a, b = s.tick(0.66, raw, pred, tcp, TZ), ref.tick(0.66, raw, pred, tcp, TZ)
    assert b.allowed and float(np.linalg.norm(b.pos_w - tcp)) > 1e-4  # the reference skill does move
    np.testing.assert_allclose(a.pos_w, b.pos_w)


def test_astra_run_instruction_stage_change_also_clears_the_bias():
    s, g, tcp = _lifted_skill_with_bias()
    assert s.astra_advance("run_instruction", 1.0, {**HOLD, "lifted(o3)": True}) == "applied"
    assert s.stage == "S2" and np.all(s.bias == 0.0)
    assert [e["why"] for e in s.events if e.get("event") == "bias_cleared"] == ["stage_S2"]


def test_step_outcome_thresholds():
    s, tcp = _skill()
    assert s.step_outcome(tcp)[0] == "OK"
    assert s.step_outcome(tcp + [0.03, 0, 0])[0] == "LAG"
    assert s.step_outcome(tcp + [0.08, 0, 0])[0] == "DEVIATE"


def test_residual_hook_bounded_and_near_only():
    q = np.zeros(7)
    np.testing.assert_allclose(apply_residual(q, residual_hook_zero, {}, near=True), q)
    big = lambda ctx: np.full(7, 1.0)
    np.testing.assert_allclose(apply_residual(q, big, {}, near=True), np.full(7, 0.02))
    np.testing.assert_allclose(apply_residual(q, big, {}, near=False), q)


def test_grasp_depth_floor_keeps_the_tcp_at_the_planner_height():
    """Decisions use the finger-link midpoint (labels_v2); the TCP (pad centre) must not sink below the planner's
    grasp height - 3 mm (deeper grasps put the gripper body on the rim), and reaching that floor counts as reached."""
    grasp_tcp_z = 0.0475 + 0.0475 - 0.018
    tcp = np.array([0.40, -0.20, grasp_tcp_z - 0.003]) + [0, 0, TZ]  # at the floor
    g_fm = (0.40, -0.20, grasp_tcp_z - 0.003 + 0.012)  # finger midpoint 1.2 cm above the TCP: labels say "down"
    s = PickPlaceSkill(dt=0.01)
    s.reset(0.0, tcp, [1, 0, 0, 0])
    s.begin_slot(0, {**DEC, "dir_xy": "none_xy", "dir_z": "down", "mag_coarse": "small", "phase": "continue"})
    c = s.tick(0.0, _raw(g_fm), OPEN, tcp, TZ)
    assert c.pos_w[2] >= tcp[2] - 1e-9  # no further descent below the floor
    s.begin_slot(1, {**DEC, "dir_xy": "none_xy", "dir_z": "down", "mag_coarse": "small", "phase": "next"})
    s.tick(0.33, _raw(g_fm), OPEN, tcp, TZ)
    assert s.phase == "close"


def test_reanchor_after_deviate_resets_the_reference():
    """M4 (b) DEVIATE: the executor re-plans from the measured state, so the same deviation is not re-reported every
    step (R5 SFT run: a 40 mm push at close gave DEVIATE -> epoch+1 -> all votes dropped -> no motion, a livelock)."""
    s, tcp = _skill()
    pushed = tcp + [0.04, 0.0, 0.03]
    assert s.step_outcome(pushed)[0] == "DEVIATE"
    s.reanchor(pushed)
    assert s.step_outcome(pushed)[0] == "OK"
