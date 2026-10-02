import numpy as np
import pytest

from harvest.l9 import bimanual9 as B


def test_bim_a_defs_12_handover_dirs():
    assert len(B.BIM_A_DEFS) == 12
    for name, d in B.BIM_A_DEFS.items():
        assert d["giver"] in ("left", "right") and d["receiver"] in ("left", "right")
        assert d["giver"] != d["receiver"]
        assert name.endswith("_lr") or name.endswith("_rl")
        if name.endswith("_lr"):
            assert d["giver"] == "left" and d["receiver"] == "right"
        else:
            assert d["giver"] == "right" and d["receiver"] == "left"
        assert isinstance(d["cats"], tuple) and len(d["cats"]) >= 1


def test_bim_a_defs_cover_six_object_groups():
    groups = {name.rsplit("_", 1)[0].split("handover_", 1)[1] for name in B.BIM_A_DEFS}
    assert groups == set(B.BIM_A_OBJECTS)


def test_handover_zone_ai_worker_midline_and_above_table():
    z = B.handover_zone_xyz("ffw_sg2", table_z=0.85)
    assert z[1] == pytest.approx(0.0)  # shared midline (both arms mirrored about y)
    assert z[2] > 0.85  # above the table, not resting on it (in-air handover)
    assert 0.30 <= z[0] <= 0.55


@pytest.mark.parametrize("profile", ["r1pro", "g1"])
def test_handover_zone_v2_profiles_defined(profile):
    z = B.handover_zone_xyz(profile, table_z=0.80)
    assert z.shape == (3,)
    assert z[2] > 0.80


def test_final_spot_moves_into_receivers_own_side():
    zone = np.array([0.4, 0.0, 1.05])
    right = B.final_spot_xyz(zone, "right")
    left = B.final_spot_xyz(zone, "left")
    assert right[1] < 0.0  # right arm's side = -y
    assert left[1] > 0.0  # left arm's side = +y
    assert right[2] < zone[2] and left[2] < zone[2]  # comes to rest, not held mid-air


def test_bim_command_schema_fields():
    c = B.bim_command("left", "support", [0.4, 0.1, 1.0], "hold", quat_wxyz=[1, 0, 0, 0], sync=True)
    assert c["arm"] == "left" and c["role"] == "support" and c["gripper"] == "hold" and c["sync"] is True
    assert c["position_m"] == [0.4, 0.1, 1.0]
    assert c["quat_wxyz"] == [1.0, 0.0, 0.0, 0.0]


def test_bim_command_rejects_bad_role_and_gripper():
    with pytest.raises(ValueError):
        B.bim_command("left", "bogus", [0, 0, 0], "grasp")
    with pytest.raises(ValueError):
        B.bim_command("left", "lead", [0, 0, 0], "bogus")


def test_bim_command_allows_hold_which_v1_schema_did_not():
    # the research doc's one new gripper value; must not collide with the existing grasp/release/keep vocabulary
    assert "hold" in B.GRIPPERS
    B.bim_command("right", "support", [0, 0, 0], "hold")  # no raise


def test_pair_commands_one_per_arm():
    a = B.bim_command("left", "lead", [0, 0, 0], "grasp")
    b = B.bim_command("right", "support", [0, 0, 0], "hold")
    call = B.pair_commands(a, b)
    assert call["commands"] == [a, b]
    assert {c["arm"] for c in call["commands"]} == {"left", "right"}


def test_phase_fsm_full_sequence():
    p = "giver_pick"
    p = B.handover_phase(p, giver_holding=False, giver_at_zone=False, receiver_contacted=False,
                         giver_opened=False, receiver_at_final=False)
    assert p == "giver_pick"  # no-op until the giver actually holds
    p = B.handover_phase(p, True, False, False, False, False)
    assert p == "giver_carry"
    p = B.handover_phase(p, True, False, False, False, False)
    assert p == "giver_carry"  # not at the zone yet
    p = B.handover_phase(p, True, True, False, False, False)
    assert p == "giver_hold"
    p = B.handover_phase(p, True, True, False, False, False)
    assert p == "receiver_pick"  # giver_hold always advances (the receiver starts approaching while it holds)
    p = B.handover_phase(p, True, True, False, False, False)
    assert p == "receiver_pick"  # no overlap contact yet
    p = B.handover_phase(p, True, True, True, False, False)
    assert p == "giver_release"
    p = B.handover_phase(p, True, True, True, False, False)
    assert p == "giver_release"  # giver hasn't opened yet
    p = B.handover_phase(p, True, True, True, True, False)
    assert p == "receiver_carry"
    p = B.handover_phase(p, True, True, True, True, True)
    assert p == "done"


def test_phase_fsm_rejects_unknown_phase():
    with pytest.raises(ValueError):
        B.handover_phase("not_a_phase", True, True, True, True, True)


def test_success_a_gate():
    g = B.success_a((0.40, 0.01), (0.40, 0.0), overlap_ticks=3)
    assert g["ok"] is True and g["place_err_m"] == pytest.approx(0.01, abs=1e-4)
    bad_far = B.success_a((0.40, 0.10), (0.40, 0.0), overlap_ticks=3)
    assert bad_far["ok"] is False
    bad_floor = B.success_a((0.40, 0.0), (0.40, 0.0), floor_touched=True, overlap_ticks=3)
    assert bad_floor["ok"] is False
    bad_no_overlap = B.success_a((0.40, 0.0), (0.40, 0.0), overlap_ticks=0)
    assert bad_no_overlap["ok"] is False
