import numpy as np

from harvest.jcr import features as FT
from harvest.jcr import truth as T
from harvest.jcr.exec_jcr import JcrExec, envelope_clip
from .test_exec_truth import Fake


class TruthClient:
    """A fake JCR that answers with the truth chunk (privileged, test only) and a close event at arrival."""

    def __init__(self, w, true):
        self.w, self.true = w, np.asarray(true, float)

    def act(self, s, head, wrist, seed=0):
        c, _ = T.project_ball(self.true, s["goal_cmd"])
        P, _ = T.smooth_chunk(s["p_cmd"], s["v"], c)
        d = (P - np.asarray(s["p_cmd"])).tolist()
        ev = np.zeros(FT.N_EVENT)
        near = np.linalg.norm(np.asarray(s["tcp"]) - c) < T.REACH_M
        ev[1 if (near and s["allow"] == "close") else 0] = 1
        return {"delta": d, "event_p": ev.tolist(), "contact_p": 0.0, "anomaly_p": [0.0] * 6, "latency_s": 0.01}


def obs():
    return {"head": np.zeros((4, 4, 3)), "wrist": np.zeros((4, 4, 3)), "q": [0.0] * 7, "grip_w": 0.1, "effort": 0.0}


def test_truthful_model_reaches_and_closes_by_itself():
    w = Fake()
    true = np.array([0.45, -0.30, 0.93])
    ex = JcrExec(0.05, 0.80, w.tcp, 0.107, 0.05, (1, 0, 0, 0), w.state, client=TruthClient(w, true), obs_fn=obs)
    ex.next_meta = {"goal_true": true, "role": "approach"}
    ex.go_to(true + [0.02, 0, 0], "close", 0.0)
    evs = []
    for _ in range(400):
        cmd, _, ev = ex.tick(w.t, w.tcp)
        evs += ev
        w.tcp = cmd.copy()
        w.t += 0.05
        if not ex.busy:
            break
    assert any(e["event"] == "close" for e in evs)
    assert ex.stats["grip_jcr"] == 1 and ex.stats["grip_fallback"] == 0
    assert np.linalg.norm(w.tcp - true) < T.REACH_M
    assert all("truth_chunk" in s for s in ex.samples)


def test_envelope_clip_pulls_rows_into_tube_and_caps_speed():
    P = np.array([[0.0, 0.2, 0.0]] * 3)
    out = envelope_clip(P, [0, 0, 0], [0, 0, 0], [1.0, 0, 0], 0.03)
    assert np.all(np.linalg.norm(np.diff(np.vstack([[0, 0, 0], out]), axis=0), axis=1) <= 0.12 * 0.05 + 1e-9)
    out = envelope_clip(np.array([[0.5, 0.2, 0.0]]), [0.5, 0, 0], [0, 0, 0], [1.0, 0, 0], 0.03, v_cap=10)
    assert abs(out[0][1] - 0.04) < 1e-9
