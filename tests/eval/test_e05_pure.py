"""R6 e05: pure parts of the E0.5 replay (E §2A.3, §2A.6)."""
import math

import pytest

from harvest.eval import e05


def test_vote_steps_use_latest_snapshots_before_t_minus_dp95():
    t = {k: round(0.33 * k, 2) for k in range(8)}
    steps = e05.vote_steps(t, d_p95=0.307, n_votes=3)
    # step k votes from k-1, k-2, k-3 (t_k - 0.307 falls just after t_{k-1}); first full step is k = 3
    assert steps[0][0] == 3
    ks = [kv for kv, _ in steps[0][1]]
    assert ks == [2, 1, 0]
    rel = [r for _, r in steps[0][1]]
    assert rel == pytest.approx([-0.33, -0.66, -0.99])
    assert [s[0] for s in steps] == [3, 4, 5, 6, 7]


def test_vote_steps_larger_latency_shifts_votes_back():
    t = {k: round(0.33 * k, 2) for k in range(8)}
    steps = e05.vote_steps(t, d_p95=0.40, n_votes=3)
    assert steps[0][0] == 4 and [kv for kv, _ in steps[0][1]] == [2, 1, 0]  # lag 2 snapshots


def test_rules_on_votes():
    v = [{"t_req": -0.33, "key": "a"}, {"t_req": -0.66, "key": "b"}, {"t_req": -0.99, "key": "b"}]
    r = e05.apply_rules(v)
    assert r["newest"] == "a" and r["la2"] == "b"
    assert r["la2_confirmed"] is True
    v2 = [{"t_req": -0.33, "key": "a"}, {"t_req": -0.66, "key": "b"}, {"t_req": -0.99, "key": "c"}]
    r2 = e05.apply_rules(v2)
    assert r2["la2"] == "c" and r2["la2_confirmed"] is False  # no consensus -> tentative = first vote


def test_same_time_flip():
    assert e05.same_time_flip(["a", "a", "a"]) is False
    assert e05.same_time_flip(["a", "b", "a"]) is True


def test_successive_flip_pairs():
    assert e05.successive_flips(["a", "a", "b", "b", "a"]) == [0, 1, 0, 1]


def test_c_flip_formulas():
    cur, prev = ["a", "a", "b"], ["a", "a", "a"]
    assert e05.c_flip_tv(cur, prev) == pytest.approx(1 / 3)
    assert e05.c_flip_one(["a", "b", "b"]) == pytest.approx(0.5)  # newest-first order, one of two pairs differs
    assert e05.c_flip_one(["a", "a", "a"]) == 0.0


def test_c2prime_follows_newest_vote_when_s1_is_uniform_like():
    opts = ["up", "down", "none_z", "NONE_ESCALATE"]
    p = e05.c2prime_probs("dir_z", opts, s1_key="up", vlm_key="down", dt=0.33)
    alpha = 3 / 4 * math.exp(-0.33 / 5)
    assert sum(p.values()) == pytest.approx(1.0)
    assert max(p, key=p.get) == "down"  # alpha ~0.7 on Sim, newest vote wins
    p0 = e05.c2prime_probs("dir_z", opts, s1_key="up", vlm_key="down", dt=6.0)  # past the 5 s timeout: S1 only
    assert max(p0, key=p0.get) == "up"
    assert alpha > 0.5


def test_c2prime_geometric_sim_prefers_the_nearest_direction():
    opts = ["plus_x", "plus_x_plus_y", "plus_y", "minus_x", "none_xy", "NONE_ESCALATE"]
    p = e05.c2prime_probs("dir_xy", opts, s1_key=None, vlm_key="plus_x", dt=0.33)
    assert p["plus_x_plus_y"] > p["minus_x"]


def test_c2prime_score_fusion_argmax():
    opts = ["continue", "next", "hold", "NONE_ESCALATE"]
    assert e05.c2prime_score_choice("phase", opts, s1_key="next", vlm_key="continue", dt=0.33) in opts


def test_a3_name_meaning_maps_shown_name_to_original_key():
    from harvest.jevcall import DIR_Z
    from harvest.options import variant
    a3 = variant(DIR_Z, "A3", 0)
    meaning = e05.name_meaning(DIR_Z)
    # A3 shows key 'up' with the name 'down' (rotated by one); an answer 'down' in A3 means 'down' by name
    shown = {o.key: o.name for o in a3}
    assert meaning[shown["up"]] == "down"


def test_perturb_window_marks_steps_after_the_event():
    assert e05.in_perturb_window(2.9, [2.55], win=1.0) is True
    assert e05.in_perturb_window(2.5, [2.55], win=1.0) is False
    assert e05.in_perturb_window(3.6, [2.55], win=1.0) is False


def test_floor_block_diff_is_signed_max_of_lower_bounds():
    # identical blocks -> no effect; block 1 always flips -> effect
    a = {("P0", 1): [0, 0, 0], ("P0", 2): [0, 0, 0]}
    b = {("P0", 1): [1, 1, 1], ("P0", 2): [1, 1, 1]}
    assert e05.block_diff_lo([a, a], n=200) <= 0
    assert e05.block_diff_lo([a, b], n=200) > 0


# ------------------------------------------------------------------------------------------ analyze (synthetic)
Q = ("dir_z", "target")
OPTS = {"dir_z": ["up", "down", "none_z", "NONE_ESCALATE"], "target": ["o3", "o5", "NONE_ESCALATE"]}
NAMES = {"dir_z": {"up": "up", "down": "down", "none_z": "none_z", "NONE_ESCALATE": "NONE_ESCALATE"},
         "target": {"o3": "o3", "o5": "o5", "NONE_ESCALATE": "NONE_ESCALATE"}}


def _synth(n_ep=6, n_k=10, flip=False, kind="P0"):
    eps, ans, truth = [], {}, {}
    for s in range(n_ep):
        eps.append({"cluster": (kind, s), "kind": kind, "seed": s, "success": True, "events_t": [1.0] if kind != "P0"
                    else [], "t": {k: round(0.33 * k, 2) for k in range(n_k)}})
        for k in range(n_k):
            key = (kind, s, k)
            z = ("up" if k % 2 else "down") if flip else "down"
            vote = {"dir_z": z, "target": "o3"}
            v = {q: {"key": vote[q], "name": NAMES[q][vote[q]]} for q in Q}
            ans[key] = {"vote": vote, "same": [dict(vote)] * 3, "var": {x: v for x in ("A1", "A2", "A3", "A4")},
                        "rt": {0: [dict(vote), dict(vote)], 1: [dict(vote), dict(vote)]}, "s1": {"dir_z": "down",
                                                                                                 "target": "o3"},
                        "opts": OPTS, "names": NAMES}
            truth[key] = {"dir_z": {"down"}, "target": {"o3"}}
    return eps, ans, truth


def test_analyze_constant_answers_narrow_claim_to_b():
    eps, ans, truth = _synth()
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=200)
    j = r["judge_input"]
    assert j["flip_rate_success"] == 0.0 and j["same_time_flip"] == 0.0
    assert j["gain_la2"] == 0.0 and j["gain_c2pp"] == 0.0
    jd = r["judgments"]
    assert jd["claim"] == "narrow_to_b" and jd["c5a3_caveat"] is True
    assert r["rules"]["pooled"]["newest"]["mean"] == 1.0
    assert set(j["layers"]) == {"L3_6"}  # dir_z k=4, target k=3
    assert r["floor"]["pooled"]["mean"] == 0.0


def test_analyze_alternating_answers_flip_every_step():
    eps, ans, truth = _synth(flip=True)
    r = e05.analyze(eps, ans, truth, questions=Q, d_p95=0.307, n_boot=200)
    # dir_z flips at every successive snapshot, target never -> pooled over the two questions 0.5
    assert r["judge_input"]["flip_rate_success"] == 0.5
    assert r["flip"]["per_question"]["dir_z"]["success"]["mean"] == 1.0
    # LA-2 on (x, y, x) picks the mode = the older pair; newest is right half of the time
    assert r["rules"]["per_question"]["dir_z"]["newest"]["mean"] is not None
