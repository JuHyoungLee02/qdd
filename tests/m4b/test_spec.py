"""E-M4b-meas FI-DEV spec (pure): seeds, conditions, injections, blind FSM, expectation table, truth, onset."""
import pytest

from harvest.m4b import spec as S


def test_only_dev_seeds():
    for s in (0, 29):
        assert S.check_fi_seed(s) == s
    for bad in (30, 500, 549, 1000, 1149, 1300, 1329, 2000, -1):
        with pytest.raises(ValueError):
            S.check_fi_seed(bad)


def test_split_and_folds():
    assert [S.seed_split(s) for s in (0, 14, 15, 29)] == ["cal", "cal", "eval", "eval"]
    assert [S.cal_fold(s) for s in (0, 4, 5, 9, 10, 14)] == [0, 0, 1, 1, 2, 2]
    assert S.cal_fold(15) is None
    assert {S.seed_kind(s) for s in range(15, 30)} == {"P0", "P1", "P2"}
    assert [S.seed_kind(s) for s in range(15, 30)].count("P1") == 5


def test_conditions_count_270():
    assert len(S.CONDITIONS) == 9 and len(S.FAILURES) == 5 and len(S.HARMLESS) == 3
    assert len([(s, c) for s in range(30) for c in S.CONDITIONS]) == 270


def test_inject_params_deterministic_and_sized():
    a, b = S.inject_params(3, "F1_grasp_miss"), S.inject_params(3, "F1_grasp_miss")
    assert a == b
    assert abs(abs(a["offset_xy"][1]) - S.F1_OFFSET_M) < 1e-12 and a["offset_xy"][0] == 0.0
    f5 = S.inject_params(3, "F5_stall")
    assert abs(abs(f5["offset_xy"][0]) - S.F5_OFFSET_M) < 1e-12 and f5["offset_xy"][1] == 0.0
    f4 = S.inject_params(7, "F4_place_off")
    assert abs(abs(f4["offset_xy"][1]) - S.F4_OFFSET_M) < 1e-12
    assert S.inject_params(3, "nominal") == {}
    signs = {S.inject_params(s, "F1_grasp_miss")["offset_xy"][1] > 0 for s in range(30)}
    assert signs == {True, False}


def st(**kw):
    base = dict(reached=False, t_in_phase=0.0, holding=False, lift_h=0.0, contact_under=False)
    base.update(kw)
    return base


def test_blind_fsm_ignores_holding_and_timeouts_advance():
    assert S.next_phase_blind("close", st(t_in_phase=0.7, holding=False)) == "lift"
    assert S.next_phase_blind("close", st(t_in_phase=0.3)) == "close"
    assert S.next_phase_blind("lift", st(reached=True, lift_h=0.0)) == "carry"
    assert S.next_phase_blind("carry", st(holding=False)) == "carry"
    assert S.next_phase_blind("descend", st(t_in_phase=5.1)) == "close"  # stall: timeout moves on
    assert S.next_phase_blind("retreat", st(t_in_phase=3.1)) == "done"
    assert S.next_phase_blind("place_descend", st(contact_under=True)) == "open"
    assert S.next_phase_blind("open", st(t_in_phase=0.6)) == "retreat"
    assert S.next_phase_blind("done", st()) == "done"


def test_expectation_and_violations():
    ok_carry = {"holding_t": True, "gripper_open": False, "lifted_holding": True, "lifted_t": True}
    assert S.violations("carry", ok_carry) == []
    assert S.violations("carry", dict(ok_carry, holding_t=False, lifted_holding=False)) == [
        "holding_t", "lifted_holding"]
    assert S.violations("close", {"holding_t": False}) == []  # transitional phase: no checks
    pd = {"holding_t": True, "gripper_open": False, "above_tp": False, "contact_tp": True}
    assert S.violations("place_descend", pd) == []  # over the tray = above OR in contact
    assert S.violations("place_descend", dict(pd, contact_tp=False)) == ["above_tp|contact_tp"]
    assert S.violations("retreat", {"on_tp": None, "holding_t": False}) == []  # unknown never violates
    assert S.violations("descend", {"gripper_open": True, "holding_t": False, "contact_stall": True}) == [
        "contact_stall"]


def test_onset_first_violation_after_injection():
    times = [0.0, 0.33, 0.66, 0.99, 1.32]
    phases = ["carry"] * 5
    good = {"holding_t": True, "gripper_open": False, "lifted_holding": True, "lifted_t": True}
    bad = dict(good, holding_t=False)
    truths = [bad, good, good, bad, bad]
    assert S.onset(times, phases, truths, t_inject=0.5) == 0.99  # the earlier violation is before injection
    assert S.onset(times, phases, [good] * 5, t_inject=0.0) is None


def test_truth_from_registry():
    pred = {"on(o3,o5)": True, "in_contact(o3,o5)": True, "lifted(o3)": False, "near(o3,o5)": False,
            "above(o3,o5)": False, "gripper_open": True, "holding(o3)": False}
    t = S.truth(pred, contact_open=False)
    assert t["on_tp"] is True and t["contact_tp"] is True and t["lifted_holding"] is False
    assert t["contact_stall"] is False and t["gripper_open"] is True
    t2 = S.truth(dict(pred, **{"holding(o3)": True, "lifted(o3)": True}), contact_open=True)
    assert t2["lifted_holding"] is True and t2["contact_stall"] is True
    assert set(t) == set(S.WORLD) | set(S.ROBOT)


def test_contact_open_needs_open_gripper_and_object_contact():
    assert S.contact_open(width=0.09, gripper_contacts={"o3"}) is True
    assert S.contact_open(width=0.06, gripper_contacts={"o3"}) is False
    assert S.contact_open(width=0.09, gripper_contacts=set()) is False
