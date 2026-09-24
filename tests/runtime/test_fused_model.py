"""Fused stage-B runtime adapter (pre-R7 fix 1): pure pieces, the HTTP client against a fake model process, and the
runtime's use of verification-head outputs (M4 (b)(2) world side + M7 critic, canon §64) on the fake world."""
import json
import math

import httpx
import numpy as np
import pytest

from harvest.runtime import fused_model as FM
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.measure import PREDS, VerifyCal
from harvest.runtime.models import MockFusedModel, ModelResult, build_live_request

from .fakeworld import FakeWorld


def test_proprio23_maps_the_8d_observation():
    jp = np.r_[np.arange(7) * 0.1, 0.07]
    prev = jp - np.r_[np.full(7, 0.001), -0.0005]
    p = FM.proprio23(jp, prev, 0.01, [0.5] * 7)
    assert p["q"] == pytest.approx(list(np.arange(7) * 0.1))
    assert p["qd"] == pytest.approx([0.1] * 7) and p["grip"] == pytest.approx([0.07, -0.05])
    assert p["tau"] == [0.5] * 7  # not observed -> training mean (normalized 0)
    assert FM.proprio23(jp, None, None, [0.0] * 7)["qd"] == [0.0] * 7
    from harvest.train import stageb_data as D
    assert len(D.proprio_vec(p)) == D.PROPRIO_DIM == 23


def test_names_and_answers_map_keys_and_names():
    raw = {"grip": {"pos": [0.3, -0.1, 0.25], "w": 0.107, "effort": 0.0},
           "objs": {k: {"pos": [0.4, -0.2, 0.05], "quat": [1, 0, 0, 0], "he": [0.03, 0.03, 0.05]} for k in ("o3", "o5")},
           "contacts": [], "support": {}}
    req, shown = build_live_request(3, "approach", "t_state: f3 (t=1.00s)  contract: c1  stage: S1 \"pick up mug o3\"\n"
                                    "robot: gripper=open arm=moving", ["o3", "o5"], raw, state="IMG")
    assert "objects" not in req["state"] and "robot: gripper=open" in req["state"]  # IMG state: no M1 coordinates
    probs = {}
    for qid, (q, opts) in shown.items():
        names = [o.name for o in opts]
        probs[qid] = {n: (0.7 if i == 1 else 0.3 / (len(names) - 1)) for i, n in enumerate(names)}
    ans = FM.answers_from(probs, shown)
    for qid, (q, opts) in shown.items():
        assert ans[q]["choice"] == opts[1].key and ans[q]["p_chosen"] == pytest.approx(0.7)
        assert set(ans[q]["probs"]) == {o.key for o in opts}
    k2n = {q: {o.key: o.name for o in opts} for q, opts in shown.values()}
    q0, opts0 = next(iter(shown.values()))
    assert FM.names_of({q0: opts0[1].key, "phase": None}, k2n) == {q0: opts0[1].name}
    sm = FM.softmax_names({"a": math.log(0.2), "b": math.log(0.6)})
    assert sm["b"] == pytest.approx(0.75)


def test_gpu_gate_serves_a_waiting_chunk_before_waiting_decides():
    import threading
    import time
    eng = FM.StageBFused.__new__(FM.StageBFused)
    eng._cv, eng._busy, eng._chunk_waiting = threading.Condition(), False, 0
    order = []

    def job(name, chunk):
        with eng._gpu(chunk):
            order.append(name)
    g = eng._gpu(False)
    g.__enter__()  # a decide is running
    ts = [threading.Thread(target=job, args=("decide2", False))]
    ts[0].start()
    time.sleep(0.05)
    ts.append(threading.Thread(target=job, args=("chunk", True)))
    ts[1].start()
    time.sleep(0.05)
    g.__exit__(None, None, None)
    for t in ts:
        t.join(2)
    assert order == ["chunk", "decide2"]


def _fake_server(record):
    def handler(req: httpx.Request):
        if req.url.path == "/info":
            return httpx.Response(200, json={"model_id": "stageb:fake", "tau_fill": [0.0] * 7, "hz": 30})
        d = json.loads(req.content)
        record.append((req.url.path, d))
        if req.url.path == "/decide":
            probs = {qid: {n: 1.0 / len(spec["criteria"]) for n in spec["criteria"]}
                     for qid, spec in d["req"]["questions"].items()}
            first = {qid: next(iter(spec["criteria"])) for qid, spec in d["req"]["questions"].items()}
            for qid, n in first.items():
                probs[qid][n] += 0.5
            return httpx.Response(200, json={"probs": probs, "verify": {p: -4.0 for p in PREDS},
                                             "meta": {"t_decide_s": 0.1, "t_verify_s": 0.001}})
        if req.url.path == "/chunk":
            return httpx.Response(200, json={"chunk": [d["proprio"]["q"] + [d["proprio"]["grip"][0]]] * 15,
                                             "chunk_dt": 1 / 30, "meta": {"t_expert_s": 0.03}})
        return httpx.Response(404, json={"error": "?"})
    return httpx.MockTransport(handler)


def test_fused_client_round_trip():
    rec = []
    c = FM.FusedClient("http://fake", transport=_fake_server(rec))
    w = FakeWorld()
    img = np.zeros((376, 672, 3), np.uint8)
    raw = w.m1()["raw"]
    req, shown = build_live_request(0, "approach", "t_state: f0\nrobot: gripper=open", ["o3", "o5"], raw, state="IMG")
    r = c.decide({"t_state": 0.0, "ctx_text": "ctx", "req": req, "shown": shown,
                  "images": {"cam_head": img, "cam_wrist_right": img[:240, :424]}})
    assert r.error is None and r.verify["on_tp"] == -4.0 and set(r.answers) == {q for q, _ in shown.values()}
    path, d = rec[-1]
    assert path == "/decide" and set(d["images"]) == {"cam_head", "cam_wrist_right"}
    committed = {q: a["choice"] for q, a in r.answers.items()}
    ch = c.chunk({"t_state": 0.2, "ctx_text": "ctx", "joint_pos": np.r_[np.zeros(7), 0.1],
                  "joint_pos_prev": np.r_[np.zeros(7), 0.1], "dt_prev": 0.01, "phase": "approach",
                  "images": {"cam_head": img, "cam_wrist_right": img[:240, :424]}}, committed)
    assert ch.error is None and ch.chunk.shape == (15, 8) and ch.chunk_dt == pytest.approx(1 / 30)
    path, d = rec[-1]
    names = {q: dict((o.key, o.name) for o in opts)[committed[q]] for q, opts in shown.values()}
    assert path == "/chunk" and d["committed"] == names  # keys -> decision-token names
    bad = FM.FusedClient("http://fake", transport=httpx.MockTransport(
        lambda q: httpx.Response(200, json={"model_id": "x", "tau_fill": [0] * 7}) if q.url.path == "/info"
        else httpx.Response(500, json={"error": "boom"})))
    r = bad.decide({"t_state": 0.0, "ctx_text": "", "req": req, "shown": shown, "images": {}})
    assert r.error and "boom" in r.error


class VerifyingFused(MockFusedModel):
    """MockFusedModel + verification-head logits: `lifted_t` is claimed FALSE whenever the skill is carrying."""

    def __init__(self, liar=False):
        super().__init__(latency_s=0.30)
        self.liar = liar

    def decide(self, ctx):
        r = super().decide(ctx)
        lg = {p: -5.0 for p in PREDS}
        if ctx["phase"] in ("lift", "carry", "place_descend"):
            lg.update(holding_t=5.0, lifted_holding=5.0, lifted_t=-5.0 if self.liar else 5.0)
        if ctx["phase"] in ("approach", "descend"):
            lg.update(gripper_open=5.0)
        if ctx["phase"] == "place_descend":
            lg.update(above_tp=5.0)
        if ctx["phase"] in ("open", "retreat", "done"):
            lg.update(on_tp=5.0, contact_tp=5.0, gripper_open=5.0)
        r.verify = lg
        return r


def _drive(model, seconds, cal=None, backend="modular"):
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="none")
    rt = OursRuntime(cfg, model)
    if cal is not None:
        rt.vcal = cal
    rt.reset()
    w = FakeWorld()
    for _ in range(int(seconds * 100)):
        a, _ = rt.act(w.obs())
        w.step(a)
    rt.close()
    return rt, w


class ModularVerifying(VerifyingFused):
    kind = "modular"

    def decide(self, ctx):
        r = super().decide({**ctx, "privileged_s1": ctx["req"]["state"]})
        return r


def test_verify_outputs_feed_measure_and_critic():
    cal = VerifyCal(T={p: 1.0 for p in PREDS}, qhat={p: 0.1 for p in PREDS}, critic_thr=0.9)
    rt, w = _drive(ModularVerifying(liar=False), 40.0, cal)
    s = rt.summary()["measure"]
    assert s["verify_outputs"] > 50 and s["t2_checked"] > 10 and s["t2_deviate"] == 0 and s["critic_alarms"] == 0
    assert np.all(np.abs(w.mug[:2] - w.tray[:2]) < [0.09, 0.07]) and not w.held  # the task still completes
    assert rt.calls[-1]["critic"]["thr"] == 0.9


def test_world_side_contradiction_is_a_soft_deviate_and_a_critic_alarm():
    cal = VerifyCal(T={p: 1.0 for p in PREDS}, qhat={p: 0.1 for p in PREDS}, critic_thr=0.9)
    rt, w = _drive(ModularVerifying(liar=True), 12.0, cal)
    s = rt.summary()["measure"]
    assert s["t2_deviate"] >= 1 and s["critic_alarms"] >= 1
    ev = [e for e in rt.events if e["event"] == "b2_world_deviate"]
    assert ev and ev[0]["preds"] == ["lifted_t"]
    assert s["t1_contradict"] == 0  # the robot side (proprio) agrees: no hard verdict from the head
    assert any(e["event"] == "m7_critic_alarm" for e in rt.events)


def test_measured_predicates_drive_the_executor_not_the_oracle():
    """The skill's grasp check reads the T1 proprio rule: an oracle-held mug with no grip effort is NOT holding."""
    rt = OursRuntime(RuntimeConfig(backend="modular", clock="simlat", astra_mode="none"), MockFusedModel())
    rt.reset()
    w = FakeWorld()
    obs = w.obs()
    obs["m1"]["raw"]["grip"]["effort"] = 0.0
    obs["joint_pos"][7] = 0.064
    rt.act(obs)
    assert rt.meas_last["holding_t"]["value"] is False and rt.meas_last["holding_t"]["source"] == "proprio"
    assert rt.meas_last["on_tp"]["value"] is None  # no head output -> unknown
