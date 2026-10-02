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


def test_bim_bf_review_covers_every_bf_def_exactly_once():
    bf_names = set(B.BIM_B_DEFS) | set(B.BIM_C_DEFS) | set(B.BIM_D_DEFS) | set(B.BIM_E_DEFS) | set(B.BIM_F_DEFS)
    assert set(B.BIM_BF_REVIEW) == bf_names


def test_bim_bf_review_entries_have_bool_and_nonempty_reason():
    for name, (kept, reason) in B.BIM_BF_REVIEW.items():
        assert isinstance(kept, bool), name
        assert isinstance(reason, str) and len(reason) > 0, name


def test_bim_bf_review_owner_r3_counts():
    # owner r3 (10-02 22:30) review: B 6/6, C 6/6, D 0/6, E 3/4, F 3/6 kept.
    def n_kept(defs):
        return sum(1 for name in defs if B.BIM_BF_REVIEW[name][0])

    assert n_kept(B.BIM_B_DEFS) == 6
    assert n_kept(B.BIM_C_DEFS) == 6
    assert n_kept(B.BIM_D_DEFS) == 0
    assert n_kept(B.BIM_E_DEFS) == 3
    assert n_kept(B.BIM_F_DEFS) == 3


def test_kept_bim_defs_includes_all_of_a_and_only_kept_bf():
    kept = B.kept_bim_defs()
    assert set(B.BIM_A_DEFS) <= set(kept)
    for name in kept:
        if name in B.BIM_BF_REVIEW:
            assert B.BIM_BF_REVIEW[name][0]
    assert len(kept) == len(B.BIM_A_DEFS) + 18  # 12 handover + 18 kept B-F (6+6+0+3+3)


def test_handover_zone_ai_worker_within_reach_verified_box():
    z = B.handover_zone_xyz("ffw_sg2", table_z=0.85, seed=1, episode_idx=0)
    assert z.shape == (3,)
    assert z[2] > 0.85  # above the table (the common-reach box starts at table + 0.22 m, see bim_zone/ffw_sg2.json)
    assert 0.15 <= z[0] <= 0.38  # the reach-verified box's x range, with a little jitter margin
    assert -0.21 <= z[1] <= 0.21


def test_handover_zone_ai_worker_reproducible_per_seed_and_episode():
    a = B.sample_handover_zone("ffw_sg2", 0.85, seed=7, episode_idx=3)
    b = B.sample_handover_zone("ffw_sg2", 0.85, seed=7, episode_idx=3)
    assert np.allclose(a, b)  # same (seed, episode_idx) -> same draw (reproducible, not fixed-point)


def test_handover_zone_ai_worker_varies_across_episodes():
    # owner 2026-10-02: the same definition must put the robot and the object in a different spot every episode,
    # not one hardcoded point -- different episode_idx (same seed) must not collapse onto a single repeated point.
    pts = [B.sample_handover_zone("ffw_sg2", 0.85, seed=42, episode_idx=i) for i in range(12)]
    uniq = {tuple(np.round(p, 3)) for p in pts}
    assert len(uniq) >= 8


@pytest.mark.parametrize("profile", ["r1pro", "g1"])
def test_handover_zone_v2_profiles_defined(profile):
    z = B.handover_zone_xyz(profile, table_z=0.80)
    assert z.shape == (3,)
    assert z[2] > 0.80


def test_zone_point_matches_sample_zone_cell_for_ffw():
    xyz, cell = B.zone_point("ffw_sg2", table_z=0.85, seed=11, episode_idx=2)
    ref = B.sample_zone_cell("ffw_sg2", 0.85, 11, 2)
    assert np.allclose(xyz, ref["xyz"])
    assert cell is not None and cell["xyz"] is ref["xyz"] or np.allclose(cell["xyz"], ref["xyz"])


def test_zone_point_no_cell_for_non_ffw_profiles():
    xyz, cell = B.zone_point("r1pro", table_z=0.80, seed=1, episode_idx=0)
    assert xyz.shape == (3,)
    assert cell is None


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


def test_all_40_defs_and_robot_eligibility():
    assert len(B.ALL_BIM_DEFS) == 40
    assert set(B.ROBOT_CATEGORIES) == {"ffw_sg2", "r1pro", "g1"}
    assert "B" not in B.ROBOT_CATEGORIES["g1"]  # owner 10-02: G1 excluded from category B (payload)
    for robot in ("ffw_sg2", "r1pro"):
        assert set(B.ROBOT_CATEGORIES[robot]) == set("ABCDEF")


@pytest.mark.parametrize("defs,n", [(B.BIM_B_DEFS, 6), (B.BIM_C_DEFS, 6), (B.BIM_D_DEFS, 6), (B.BIM_E_DEFS, 4),
                                    (B.BIM_F_DEFS, 6)])
def test_category_def_counts(defs, n):
    assert len(defs) == n


def test_lift_phase_fsm_requires_both_closed_before_lift():
    p = "approach"
    p = B.lift_phase(p, True, False, False, False, False, False)
    assert p == "close_gate"  # one side closed moves out of "approach"...
    p = B.lift_phase(p, True, False, False, False, False, False)
    assert p == "close_gate"  # ...but the sync gate holds until BOTH are closed
    p = B.lift_phase(p, True, True, False, False, False, False)
    assert p == "lift"
    p = B.lift_phase(p, True, True, True, False, False, False)
    assert p == "carry"
    p = B.lift_phase(p, True, True, True, True, False, False)
    assert p == "place_gate"
    p = B.lift_phase(p, True, True, True, True, True, True)
    assert p == "done"


def test_lift_phase_fsm_rejects_unknown_phase():
    with pytest.raises(ValueError):
        B.lift_phase("bogus", True, True, True, True, True, True)


def test_success_b_requires_sync_gate_and_table_clearance():
    good = B.success_b((0.4, 0.0), (0.4, 0.0), both_closed_before_lift=True, min_table_gap_m=0.05)
    assert good["ok"] is True
    no_gate = B.success_b((0.4, 0.0), (0.4, 0.0), both_closed_before_lift=False, min_table_gap_m=0.05)
    assert no_gate["ok"] is False
    dragged = B.success_b((0.4, 0.0), (0.4, 0.0), both_closed_before_lift=True, min_table_gap_m=0.0)
    assert dragged["ok"] is False


def test_success_d_both_placed_no_self_collision():
    good = B.success_d((0.4, 0.1), (0.4, 0.1), (0.4, -0.1), (0.4, -0.1), self_collisions=0)
    assert good["ok"] is True
    collided = B.success_d((0.4, 0.1), (0.4, 0.1), (0.4, -0.1), (0.4, -0.1), self_collisions=1)
    assert collided["ok"] is False
    off = B.success_d((0.4, 0.2), (0.4, 0.1), (0.4, -0.1), (0.4, -0.1), self_collisions=0)
    assert off["ok"] is False


def test_best_release_yaw_never_turns_a_top_only_candidate_into_side():
    # a candidate pointing straight down (local [0,0,-1]) is invariant under any rotation about world z -- it can
    # never classify as "side" no matter which yaw is tried, so n_match must stay 0 for every yaw.
    cand = np.array([[0.0, 0.0, -1.0]])
    yaw, n_match, n_tot = B.best_release_yaw(cand, ("side",), (0.0, -0.23), (0.4, 0.0))
    assert n_tot == 1
    assert n_match == 0


def test_best_release_yaw_finds_a_top_candidate_for_a_top_zone():
    cand = np.array([[0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
    yaw, n_match, n_tot = B.best_release_yaw(cand, ("top",), (0.0, -0.23), (0.4, 0.0))
    assert n_match >= 1  # the invariant top candidate always matches a "top" zone, at any yaw


def test_best_release_yaw_picks_more_matches_when_more_are_possible():
    # two side-ish horizontal candidates, 180 deg apart: some yaw should line at least one of them up with "side"
    # or "front" (whichever the geometry gives) better than both being, say, classified as the wrong one at yaw 0.
    cand = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, -1.0, 0.0]])
    from harvest.l9 import curobo9 as C
    yaw, n_match, n_tot = B.best_release_yaw(cand, C.APPROACHES[1:], (0.0, -0.23), (0.4, 0.0), n_steps=16)
    assert n_tot == 4
    assert n_match >= 2  # at least half of 4 roughly-evenly-spread horizontal candidates should match some class


def test_success_a_gate():
    g = B.success_a((0.40, 0.01), (0.40, 0.0), overlap_ticks=3)
    assert g["ok"] is True and g["place_err_m"] == pytest.approx(0.01, abs=1e-4)
    bad_far = B.success_a((0.40, 0.10), (0.40, 0.0), overlap_ticks=3)
    assert bad_far["ok"] is False
    bad_floor = B.success_a((0.40, 0.0), (0.40, 0.0), floor_touched=True, overlap_ticks=3)
    assert bad_floor["ok"] is False
    bad_no_overlap = B.success_a((0.40, 0.0), (0.40, 0.0), overlap_ticks=0)
    assert bad_no_overlap["ok"] is False


# ---------------------------------------------------------------------------------------------- handover row (owner
# 2026-10-02, L9_PRINCIPLES.md §2 + "핸드오버는 VLM에 완전히 결합"): every field below must be a WRITTEN command,
# not live only in code.
def test_handover_direction_from_giver_arm():
    assert B.handover_direction("left") == "lr"
    assert B.handover_direction("right") == "rl"


@pytest.mark.parametrize("direction", B.DIRECTIONS)
def test_handover_rows_carry_every_required_field(direction):
    rows = B.handover_rows(direction, giver_point_px=[100, 200], giver_height=0.9, giver_approach="top",
                           giver_rot_bin=3, handover_point_px=[500, 400], handover_height=1.1,
                           receiver_point_px=[520, 410], receiver_approach="side", receiver_rot_bin=5,
                           receiver_source="graspgenx", release_sync=True)
    assert [r["phase"] for r in rows] == ["giver_pick", "giver_carry", "receiver_pick", "giver_release"]
    assert all(r["direction"] == direction for r in rows)  # direction on every row, not just one
    giver_arm, receiver_arm = ("left", "right") if direction == "lr" else ("right", "left")

    pick = rows[0]["commands"][0]
    assert pick["arm"] == giver_arm and pick["point_px"] == [100, 200] and pick["height"] == 0.9
    assert pick["approach"] == "top" and pick["wrist_bin"] == 3 and pick["gripper"] == "grasp"

    carry = rows[1]["commands"][0]
    assert carry["arm"] == giver_arm and carry["point_px"] == [500, 400] and carry["height"] == 1.1
    assert carry["gripper"] == "hold"  # the handover point as a commanded target, not live-only

    hold, grasp = rows[2]["commands"]
    assert hold["arm"] == giver_arm and hold["gripper"] == "hold" and hold["sync"] is True
    assert hold["point_px"] == [500, 400]  # same handover point repeated on the receiver_pick row
    assert grasp["arm"] == receiver_arm and grasp["point_px"] == [520, 410] and grasp["approach"] == "side"
    assert grasp["wrist_bin"] == 5 and grasp["sync"] is True and grasp["source"] == "graspgenx"

    release = rows[3]["commands"][0]
    assert release["arm"] == giver_arm and release["gripper"] == "release" and release["sync"] is True


def test_handover_rows_rejects_unknown_direction():
    with pytest.raises(ValueError):
        B.handover_rows("lrx", [0, 0], 0.9, "top", 0, [0, 0], 0.9, [0, 0], "top", 0)


def test_direction_score_gates_on_both_ik_ok():
    assert B.direction_score(True, True, path_cost=1.0, joint_margin=2.0) == pytest.approx(1.0)
    assert B.direction_score(True, False, path_cost=1.0, joint_margin=2.0) == float("-inf")
    assert B.direction_score(False, True, path_cost=1.0, joint_margin=2.0) == float("-inf")


def test_choose_direction_picks_the_better_reaching_one():
    scores = {"lr": {"giver_ik_ok": True, "receiver_ik_ok": True, "path_cost": 2.0, "joint_margin": 1.0},
              "rl": {"giver_ik_ok": True, "receiver_ik_ok": True, "path_cost": 0.5, "joint_margin": 1.0}}
    assert B.choose_direction(scores) == "rl"  # lower path cost, same margin


def test_choose_direction_skips_the_direction_that_cannot_reach():
    scores = {"lr": {"giver_ik_ok": False, "receiver_ik_ok": True, "path_cost": 0.1, "joint_margin": 5.0},
              "rl": {"giver_ik_ok": True, "receiver_ik_ok": True, "path_cost": 3.0, "joint_margin": 0.1}}
    assert B.choose_direction(scores) == "rl"  # lr can't reach at all, no matter how cheap it looks


def test_choose_direction_raises_when_neither_reaches():
    scores = {"lr": {"giver_ik_ok": False, "receiver_ik_ok": True, "path_cost": 0.1, "joint_margin": 5.0},
              "rl": {"giver_ik_ok": True, "receiver_ik_ok": False, "path_cost": 3.0, "joint_margin": 0.1}}
    with pytest.raises(ValueError):
        B.choose_direction(scores)


# ---------------------------------------------------------------- deep-dive 10-03: other hand model, sync, gates
def _inside(boxes, p):
    from harvest.l9 import grasp9 as G
    for c, ext, q in boxes.values():
        R = G.qmat(q)
        d = R.T @ (np.asarray(p, float) - np.asarray(c, float))
        if (np.abs(d) <= np.asarray(ext, float) / 2 + 1e-9).all():
            return True
    return False


def test_hand_boxes_leave_the_space_between_the_pads_free():
    from harvest.l9 import grasp9 as G
    gr = G.gripper("ffw_sg2")
    bx = B.hand_boxes(np.eye(4), gr, 0.06)
    assert not _inside(bx, [0.0, 0.0, 0.0])  # the held object's grasp point (TCP) is NOT covered
    assert not _inside(bx, [0.0, 0.02, -0.01])
    assert _inside(bx, [0.0, 0.03 + gr["finger_t"] / 2, -0.01])  # finger slab
    assert _inside(bx, [0.0, 0.0, 0.10])  # palm / wrist behind the TCP (+z_G = away from the approach)


def test_hand_boxes_follow_the_tcp_pose():
    from harvest.l9 import grasp9 as G
    gr = G.gripper("ffw_sg2")
    T = np.eye(4)
    T[:3, :3] = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])  # rot x +90: z_G -> world -y
    T[:3, 3] = [0.4, 0.1, 0.9]
    bx = B.hand_boxes(T, gr, 0.05)
    assert _inside(bx, [0.4, 0.1 - 0.10, 0.9])  # palm behind along +z_G = world -y
    assert not _inside(bx, [0.4, 0.1, 0.9])
    C, H, R = B.boxes_as_obstacles(bx)
    assert C.shape == (3, 3) and H.shape == (3, 3) and R.shape == (3, 3, 3)


def test_holding_needs_closed_command_and_a_gap_above_empty():
    assert B.holding(0.06, 0.0, 0.003)
    assert not B.holding(0.001, 0.0, 0.003)  # closed on nothing
    assert not B.holding(0.06, 0.09, 0.003)  # open


def test_side_ok_left_takes_plus_y_right_takes_minus_y():
    mid = np.array([0.12, -0.12, 0.0])
    assert list(B.side_ok(mid, 0.0, "left")) == [True, False, False]
    assert list(B.side_ok(mid, 0.0, "right")) == [False, True, False]


def test_sync_resample_gives_one_time_axis():
    a = np.linspace(0, 1, 5)[:, None] * np.ones((1, 7))
    b = np.linspace(0, 1, 11)[:, None] * np.ones((1, 7))
    ra, rb = B.sync_resample([a, b])
    assert len(ra) == len(rb) == 11
    assert np.allclose(ra[0], a[0]) and np.allclose(ra[-1], a[-1])
    assert np.allclose(ra[:, 0], rb[:, 0])  # same fraction of the path at every tick


def test_bottom_offset_upright_and_tilted():
    he = (0.05, 0.03, 0.09)
    assert abs(B.bottom_offset(np.eye(3), he) - 0.09) < 1e-9
    R = np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]])  # lying on its side
    assert abs(B.bottom_offset(R, he) - 0.05) < 1e-9


def test_success_b_needs_held_through_and_low_tilt():
    base = dict(both_closed_before_lift=True, min_table_gap_m=0.05)
    assert B.success_b((0.5, 0.0), (0.5, 0.0), **base)["ok"]
    assert not B.success_b((0.5, 0.0), (0.5, 0.0), held_through=False, **base)["ok"]
    assert not B.success_b((0.5, 0.0), (0.5, 0.0), tilt_deg=35.0, **base)["ok"]


def test_handover_compat_keeps_a_far_receiver_grasp_and_drops_an_overlapping_one():
    from harvest.l9 import grasp9 as G
    gr = G.gripper("ffw_sg2")
    top = G.frame_of([0, 0, -1.0], [0, 1.0, 0])  # approach down, close along y
    side_lo = G.frame_of([1.0, 0, 0], [0, 1.0, 0])  # approach +x, close along y
    T = np.repeat(np.eye(4)[None], 3, 0)
    T[0, :3, :3], T[0, :3, 3] = top, [0, 0, 0.10]  # giver: top of a 22 cm bottle
    T[1, :3, :3], T[1, :3, 3] = side_lo, [0, 0, -0.10]  # receiver: low on the far side
    T[2, :3, :3], T[2, :3, 3] = side_lo, [0, 0, 0.09]  # receiver: right under the giver's fingers
    C = {"T": T, "w": np.array([0.05, 0.05, 0.05]), "pre_open": np.array([0.08, 0.08, 0.08])}
    out = B.handover_compat(C, gr, [0], [1, 2])
    assert list(out[0]) == [1]
