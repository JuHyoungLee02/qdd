import numpy as np

from harvest.jcr import features as F
from harvest.jcr import truth as T


def sample(**kw):
    s = {"tcp": [0.40, -0.20, 1.00], "goal_cmd": [0.45, -0.30, 0.93], "goal_true": [0.46, -0.30, 0.93],
         "p_cmd": [0.40, -0.20, 1.005], "v": [0.0, 0.0, 0.0], "r_goal": 0.03, "allow": "close", "cmd_age": 0.4,
         "q": [0.1] * 7, "grip_w": 0.1, "effort": 0.5, "stop": False, "grip_event": "keep", "grip_row": None,
         "anomaly": []}
    c, _ = T.project_ball(s["goal_true"], s["goal_cmd"])
    s["chunk"] = T.smooth_chunk(s["p_cmd"], s["v"], c)[0].tolist()
    s.update(kw)
    return s


def test_cond_dim_and_joystick_first():
    x = F.cond_vec(sample())
    assert x.shape == (F.COND_DIM,)
    assert np.allclose(x[:3], 10 * (np.array([0.45, -0.30, 0.93]) - [0.40, -0.20, 1.00]), atol=1e-6)


def test_event_class_roundtrip():
    for s, want in ((sample(), ("keep", None)), (sample(stop=True), ("stop", None)),
                    (sample(grip_event="close", grip_row=3), ("close", 3)),
                    (sample(grip_event="open", grip_row=9), ("open", 9))):
        c = F.event_class(s)
        assert 0 <= c < F.N_EVENT and F.decode_event(c) == want


def test_branch_is_truth_relabelled_and_flags_mismatch():
    rng = np.random.default_rng(0)
    for _ in range(50):
        b = F.branch(sample(), rng, mode="A")
        c, _ = T.project_ball(b["goal_true"], b["goal_cmd"])
        assert ("cmd_mismatch" in b["anomaly"]) == T.mismatch(b["goal_true"], b["goal_cmd"])
        P, _ = T.smooth_chunk(b["p_cmd"], b["v"], c)
        assert np.allclose(b["chunk"], P) and b["grip_event"] == "keep"
        off = np.linalg.norm(np.array(b["goal_cmd"]) - b["goal_true"])
        assert 0.003 - 1e-9 <= off <= 0.06 + 1e-9


def test_norm_roundtrip():
    ss = [sample(p_cmd=[0.40, -0.20, 1.0 + 0.001 * i]) for i in range(5)]
    n = F.Norm.fit(ss)
    d = F.delta(ss[0])
    assert np.allclose(n.unz(n.z(d)), d, atol=1e-6)


def test_branch_p_label_unchanged_for_blend_rules():
    rng = np.random.default_rng(1)
    s = sample()
    for m in ("B", "C"):
        b = F.branch(s, rng, mode=m)
        assert b["chunk"] == s["chunk"] and b["goal_cmd"] != s["goal_cmd"]


def test_use_mode_picks_the_rule_label():
    s = sample()
    s["labels"] = {"P": [[1, 1, 1]] * T.H, "A": [[0, 0, 0]] * T.H}
    assert F.use_mode(s, "B")["chunk"] == [[1, 1, 1]] * T.H and F.use_mode(s, "A")["chunk"] == [[0, 0, 0]] * T.H
