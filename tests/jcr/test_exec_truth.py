import numpy as np

from harvest.jcr import truth as T
from harvest.jcr.exec_truth import DS_TICKS, TruthExec


class Fake:
    """Kinematic world: the TCP follows the command exactly; objects static unless moved."""

    def __init__(self):
        self.t, self.tcp = 0.0, np.array([0.40, -0.20, 1.00])
        self.obj = {"o3": np.array([0.45, -0.30, 0.90]), "o5": np.array([0.45, -0.10, 0.86])}
        self.holding = False

    def state(self):
        return {"t": self.t, "tcp": self.tcp.copy(), "obj": self.obj, "holding": self.holding, "upright": True,
                "touched": set(), "grip_w": 0.1}


def run(ex, w, n=400):
    evs = []
    for _ in range(n):
        cmd, width, ev = ex.tick(w.t, w.tcp)
        evs += ev
        w.tcp = cmd.copy()
        w.t += 0.05
        if not ex.busy:
            break
    return evs


def make(w):
    return TruthExec(0.05, 0.80, w.tcp, 0.107, 0.05, (1, 0, 0, 0), w.state)


def test_noisy_command_is_corrected_inside_envelope_then_grip():
    w = Fake()
    ex = make(w)
    true = np.array([0.45, -0.30, 0.93])
    ex.next_meta = {"goal_true": true, "role": "approach", "src": "upper"}
    ex.go_to(true + [0.02, 0.0, 0.0], "close", w.t)
    evs = run(ex, w)
    assert [e["event"] for e in evs][-1] == "close" or any(e["event"] == "close" for e in evs)
    assert np.linalg.norm(w.tcp - true) < T.REACH_M
    assert all(not s["anomaly"] for s in ex.samples)


def test_far_command_followed_to_boundary_and_flagged():
    w = Fake()
    ex = make(w)
    true = np.array([0.45, -0.30, 0.93])
    goal = true + [0.10, 0.0, 0.0]
    ex.next_meta = {"goal_true": true, "role": "approach"}
    ex.go_to(goal, "keep", w.t)
    run(ex, w)
    assert abs(np.linalg.norm(w.tcp - goal) - T.R_GOAL) < T.REACH_M
    assert all("cmd_mismatch" in s["anomaly"] for s in ex.samples)


def test_target_push_moves_c_star_and_labels_equal_executed_rows():
    w = Fake()
    ex = make(w)
    true = np.array([0.45, -0.30, 0.93])
    ex.next_meta = {"goal_true": true, "role": "approach"}
    ex.go_to(true, "keep", w.t)
    cmds = []
    for i in range(300):
        if i == 10:
            w.obj["o3"] = w.obj["o3"] + [0.015, 0, 0]
        cmd, _, _ = ex.tick(w.t, w.tcp)
        cmds.append(cmd)
        w.tcp = cmd.copy()
        w.t += 0.05
        if not ex.busy:
            break
    assert np.linalg.norm(w.tcp - (true + [0.015, 0, 0])) < T.REACH_M
    s = ex.samples[1]
    assert np.allclose(np.array(s["chunk"][:DS_TICKS]), np.array(cmds[s["k"]:s["k"] + DS_TICKS]))


def test_delay_keeps_previous_until_active():
    w = Fake()
    ex = make(w)
    ex.next_meta = {"goal_true": w.tcp + [0.05, 0, 0], "role": "lift", "delay_s": 1.0}
    ex.go_to(w.tcp + [0.05, 0, 0], "keep", 0.0)
    assert ex.busy and ex.seg is None
    p0 = w.tcp.copy()
    for _ in range(10):
        cmd, _, _ = ex.tick(w.t, w.tcp)
        w.tcp = cmd
        w.t += 0.05
    assert np.allclose(w.tcp, p0)
    run(ex, w)
    assert np.linalg.norm(w.tcp - (p0 + [0.05, 0, 0])) < T.REACH_M
