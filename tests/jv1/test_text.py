import numpy as np

from harvest.jcr import features as FT
from harvest.jcr import truth as T
from harvest.jv1 import text as X


def sample(**kw):
    s = {"k": 3, "t": 1.0, "tcp": [0.33, -0.25, 1.08], "p_cmd": [0.334, -0.247, 1.081], "v": [0.01, -0.02, 0.0],
         "goal_cmd": [0.447, -0.343, 1.025], "goal_true": [0.441, -0.344, 1.025], "r_goal": 0.03, "allow": "close",
         "kappa": 0.5, "height": "above", "cmd_age": 1.85, "q": [-0.98, -1.09, 1.22, -2.40, 0.52, 1.25, 1.80],
         "grip_w": 0.107, "effort": -0.08, "grip_event": "keep", "grip_row": None, "contact": False,
         "anomaly": [], "stop": False}
    s.update(kw)
    return s


def test_point_height_round_trip_is_within_2mm_over_the_workspace():
    rng = np.random.default_rng(0)
    for _ in range(500):
        p = np.array([rng.uniform(0.25, 0.65), rng.uniform(-0.45, 0.25), rng.uniform(0.86, 1.25)])
        u, v, h = X.to_pt(p)
        assert all(isinstance(a, int) for a in (u, v, h))
        q = X.from_pt(u, v, h)
        assert np.linalg.norm(q - p) < 0.002, (p, q)


def test_answer_encode_parse_round_trip():
    s = sample(grip_event="close", grip_row=3, contact=True, anomaly=["cmd_mismatch"])
    a = X.answer(s, label="P")
    out = X.parse(a)
    assert out["event"] == FT.event_class(s)
    assert out["contact"] == 1 and out["anom"][T.ANOMALIES.index("cmd_mismatch")] == 1
    assert np.linalg.norm(X.from_pt(*out["pt"]) - np.asarray(s["goal_true"])) < 0.002
    st = X.parse(X.answer(sample(stop=True), label="P"))
    assert st["event"] == FT.EV_STOP


def test_label_A_waypoint_is_the_clipped_point():
    s = sample(goal_cmd=[0.50, -0.344, 1.025])  # 5.9 cm off the true point -> clipped to the 3 cm ball
    c = X.waypoint(s, "A")
    assert abs(np.linalg.norm(c - np.asarray(s["goal_cmd"])) - T.R_GOAL) < 1e-9
    assert np.allclose(X.waypoint(s, "P"), s["goal_true"])


def test_parse_rejects_garbage():
    assert X.parse("hello") is None
    assert X.parse("512 433") is None


def test_rows_from_truth_waypoint_equal_the_P_label():
    s = sample()
    rows = X.rows(s, np.asarray(s["goal_true"]), stop=False)
    lab = T.mode_chunk("P", s["p_cmd"], s["v"], s["goal_true"], s["goal_cmd"])
    assert np.allclose(rows, lab)


def test_prompt_mentions_command_and_state():
    p = X.prompt(sample())
    for k in ("command", "gripper allowed close", "stage above", "tcp", "joints"):
        assert k in p
