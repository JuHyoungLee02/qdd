from harvest.analysis.replay import c2pp, judge_e05, la2, newest


def V(*pairs):
    return [{"t_req": t, "key": k} for t, k in pairs]


def test_newest_uses_request_time():
    assert newest(V((-1.0, "a"), (-0.3, "b"), (-0.6, "c"))) == "b"


def test_la2_two_of_three_is_consensus():
    assert la2(V((-1.0, "a"), (-0.6, "a"), (-0.3, "b"))) == "a"


def test_la2_no_consensus_takes_first_vote():
    assert la2(V((-0.3, "c"), (-1.0, "a"), (-0.6, "b"))) == "a"


def test_c2pp_decay_prefers_recent():
    assert c2pp(V((-1.0, "a"), (-0.3, "b"))) == "b"
    assert c2pp(V((-1.0, "a"), (-0.9, "a"), (-0.3, "b"))) == "b"  # 2×0.12 < 0.53


def test_judgment1_narrows_claim():
    r = {"flip_rate_success": 0.01, "gain_la2": 0.005, "gain_c2pp": 0.004, "gain_la2_lo": -0.01, "gain_c2pp_lo": -0.01}
    assert judge_e05(r)["claim"] == "narrow_to_b"


def test_judgment2_keeps_a():
    r = {"flip_rate_success": 0.08, "gain_la2": 0.03, "gain_c2pp": 0.01, "gain_la2_lo": 0.005, "gain_c2pp_lo": -0.01}
    assert judge_e05(r)["claim"] == "keep_a"


def test_judgment3_stabilizer():
    r = {"flip_rate_success": 0.08, "gain_la2": 0.01, "gain_c2pp": 0.01, "gain_la2_lo": -0.01, "gain_c2pp_lo": -0.01}
    assert judge_e05(r)["claim"] == "a_as_stabilizer"


def test_uncovered_case_reported_not_forced():
    r = {"flip_rate_success": 0.01, "gain_la2": 0.03, "gain_c2pp": 0.0, "gain_la2_lo": 0.01, "gain_c2pp_lo": -0.01}
    assert judge_e05(r)["claim"] == "undecided"


def test_judgment4_c_flip_and_6_c5a3():
    r = {"flip_rate_success": 0.05, "gain_la2": 0, "gain_c2pp": 0, "gain_la2_lo": -1, "gain_c2pp_lo": -1,
         "perturb_flip": 0.12, "auroc": {"tv_distance": 0.74, "pairwise": 0.72}, "same_time_flip": 0.004}
    out = judge_e05(r)
    assert out["c_flip_keep"] is True and out["c_flip_default"] == "tv_distance" and out["c5a3_caveat"] is True
    r["auroc"] = {"tv_distance": 0.70, "pairwise": 0.75}
    assert judge_e05(r)["c_flip_default"] == "pairwise"


def test_judgment9_layers():
    layers = {"L2": {"a1_minus_a0_lo": -0.01, "a3_follow_minus_floor_lo": 0.02, "a0_minus_a1_lo": -0.03, "a4_flip": 0.01},
              "L3_6": {"a1_minus_a0_lo": -0.08, "a3_follow_minus_floor_lo": -0.01, "a0_minus_a1_lo": 0.02, "a4_flip": 0.06}}
    out = judge_e05({"flip_rate_success": 0.1, "gain_la2": 0, "gain_c2pp": 0, "gain_la2_lo": -1, "gain_c2pp_lo": -1,
                     "layers": layers, "block_diff_lo": 0.01})
    assert out["name_rule"] == {"L2": "neutral", "L3_6": "keep"}
    assert out["c3pp_required"] is True and out["time_block_effect"] is True
