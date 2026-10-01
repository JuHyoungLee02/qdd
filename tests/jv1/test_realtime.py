import numpy as np

from harvest.jcr import features as FT
from harvest.jcr import truth as T
from harvest.jcr.exec_jcr import JcrExec
from harvest.jv1 import text as X
from harvest.jv1.realtime import DelayedClient, TruthWaypointClient


class Fake:
    """Kinematic world (as tests/jcr/test_exec_truth.Fake)."""

    def __init__(self):
        self.t, self.tcp = 0.0, np.array([0.40, -0.20, 1.00])
        self.obj = {"o3": np.array([0.45, -0.30, 0.90]), "o5": np.array([0.45, -0.10, 0.86])}
        self.holding = False

    def state(self):
        return {"t": self.t, "tcp": self.tcp.copy(), "obj": self.obj, "holding": self.holding, "upright": True,
                "touched": set(), "grip_w": 0.1}


class TruthClient:
    """Fake arm A (as tests/jcr/test_exec_jcr.TruthClient): truth chunk, close at arrival."""

    def __init__(self, w, true):
        self.w, self.true = w, np.asarray(true, float)

    def act(self, s, head, wrist, seed=0):
        c, _ = T.project_ball(self.true, s["goal_cmd"])
        P, _ = T.smooth_chunk(s["p_cmd"], s["v"], c)
        ev = np.zeros(FT.N_EVENT)
        near = np.linalg.norm(np.asarray(s["tcp"]) - c) < T.REACH_M
        ev[1 if (near and s["allow"] == "close") else 0] = 1
        return {"delta": (P - np.asarray(s["p_cmd"])).tolist(), "event_p": ev.tolist(), "contact_p": 0.0,
                "anomaly_p": [0.0] * 6, "latency_s": 0.01}


def obs():
    return {"head": np.zeros((4, 4, 3)), "wrist": np.zeros((4, 4, 3)), "q": [0.0] * 7, "grip_w": 0.1, "effort": 0.0}


class WaypointClient(TruthClient):
    """Fake arm B: waypoint answer (c_hat) + controller rows, close at arrival."""

    def act(self, s, head, wrist, seed=0):
        o = super().act(s, head, wrist, seed)
        o["c_hat"] = T.project_ball(self.true, s["goal_cmd"])[0].tolist()
        return o


def smp(t=1.0, k=20):
    return {"t": t, "k": k, "p_cmd": [0.40, -0.20, 1.00], "v": [0.0, 0.0, 0.0], "tcp": [0.40, -0.20, 1.00],
            "goal_cmd": [0.45, -0.30, 0.93], "allow": "close"}


def test_zero_delay_passes_the_answer_through():
    true = np.array([0.45, -0.30, 0.93])
    for inner in (TruthClient(None, true), WaypointClient(None, true)):
        o0 = inner.act(smp(), None, None)
        o1 = DelayedClient(inner, 0.0, 1).act(smp(), None, None)
        assert np.allclose(o0["delta"], o1["delta"], atol=1e-9)
        assert int(np.argmax(o0["event_p"])) == int(np.argmax(o1["event_p"]))


def test_delay_holds_until_the_first_answer_lands():
    true = np.array([0.45, -0.30, 0.93])
    dc = DelayedClient(TruthClient(None, true), 0.3, 1)
    d = np.asarray(dc.act(smp(), None, None)["delta"])
    assert np.allclose(d[:6], 0.0) and np.linalg.norm(d[-1]) > 0


def test_period_calls_the_model_every_other_decision():
    true = np.array([0.45, -0.30, 0.93])
    dc = DelayedClient(WaypointClient(None, true), 0.0, 2)
    for i in range(6):
        dc.act(smp(1.0 + 0.2 * i, 20 + 4 * i), None, None)
    assert dc.calls == 3


def run(ex, w, n=600):
    evs = []
    for _ in range(n):
        cmd, _, ev = ex.tick(w.t, w.tcp)
        evs += ev
        w.tcp = cmd.copy()
        w.t += 0.05
        if not ex.busy:
            break
    return evs


def test_delayed_waypoint_arm_still_reaches_and_closes():
    w = Fake()
    true = np.array([0.45, -0.30, 0.93])
    client = DelayedClient(WaypointClient(w, true), 0.4, 2)
    ex = JcrExec(0.05, 0.80, w.tcp, 0.107, 0.05, (1, 0, 0, 0), w.state, client=client, obs_fn=obs)
    ex.next_meta = {"goal_true": true, "role": "approach"}
    ex.go_to(true + [0.02, 0, 0], "close", 0.0)
    evs = run(ex, w)
    assert any(e["event"] == "close" for e in evs)
    assert np.linalg.norm(w.tcp - true) < T.REACH_M + 0.002


def test_truth_waypoint_client_is_the_ceiling():
    w = Fake()
    true = np.array([0.45, -0.30, 0.93])
    c = TruthWaypointClient("P")
    ex = JcrExec(0.05, 0.80, w.tcp, 0.107, 0.05, (1, 0, 0, 0), w.state, client=c, obs_fn=obs)
    c.bind(ex)
    ex.next_meta = {"goal_true": true, "role": "approach"}
    ex.go_to(true + [0.02, 0, 0], "close", 0.0)
    evs = run(ex, w)
    assert any(e["event"] == "close" for e in evs)
    assert ex.stats["grip_jcr"] == 1
    assert np.linalg.norm(w.tcp - true) < 0.003  # quantisation <= 2 mm
    assert len(ex.samples[0]["jcr"]["delta"]) == T.H
    assert np.linalg.norm(X.from_pt(*X.to_pt(true)) - true) < 0.002
