"""OursRuntime end to end on a kinematic fake world (no Isaac): M1 -> calls -> simlat -> M4 -> skill S -> action."""
import numpy as np
import pytest

from harvest.runtime.astra_hb import MockAstra
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockFusedModel, MockSelector

from .fakeworld import FakeWorld


def _run(backend, model, seconds, astra=None):
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="mock" if astra else "none")
    rt = OursRuntime(cfg, model, astra=astra)
    rt.reset()
    w = FakeWorld()
    hist = []
    for _ in range(int(seconds * 100)):
        a, meta = rt.act(w.obs())
        w.step(a)
        hist.append((w.t, meta["phase"], w.held, w.mug.copy()))
    rt.close()
    return rt, w, hist


def test_modular_mock_completes_pick_and_place_on_fake_world():
    rt, w, hist = _run("modular", MockSelector(latency_s=0.30), 40.0, astra=MockAstra(3.0))
    phases = [p for _, p, _, _ in hist]
    for p in ("approach", "descend", "close", "lift", "carry", "place_descend", "open", "retreat"):
        assert p in phases, (p, sorted(set(phases)))
    assert np.all(np.abs(w.mug[:2] - w.tray[:2]) < [0.09, 0.07]) and not w.held
    s = rt.summary()
    assert s["calls_delivered"] > 100 and s["call_errors"] == 0
    assert s["decisions_per_sim_s"] == pytest.approx(1 / 0.33, rel=0.1)
    assert s["latency_s"]["p50"] == pytest.approx(0.30)
    assert 0.5 < s["commit_ratio_mean"] <= 1.0
    assert s["astra_calls"] >= 3 and s["astra_decisions"]["ack"] == s["astra_calls"]


def test_every_call_logs_its_request_hash_and_canary_id():
    """canon §42 sidecar (R7 cycle-1 D2): decision calls, chunk calls and Astra heartbeats carry the sha256 of the
    canonical request payload (image digests included) and the day's canary id (or an explicit "none")."""
    import re
    hx = re.compile(r"^[0-9a-f]{64}$")
    for backend, model in (("modular", MockSelector(latency_s=0.30)), ("fused", MockFusedModel(latency_s=0.30))):
        cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="mock", canary_id="cn20260924_abcd1234_x1",
                            hb_N_s=1.0)
        rt = OursRuntime(cfg, model, astra=MockAstra(1.0))
        rt.reset()
        w = FakeWorld()
        for i in range(400):
            o = w.obs()
            if i % 10 == 0:  # a new camera frame every 0.1 s
                o["images"] = {"cam_head": np.full((8, 8, 3), i % 251, np.uint8)}
            a, _ = rt.act(o)
            w.step(a)
        rt.close()
        heart = [a for a in rt.astra_log if "decision" in a]
        assert rt.calls and heart
        for rows in [rt.calls, heart] + ([rt.chunk_log] if backend == "fused" else []):
            assert rows
            for r in rows:
                assert hx.match(r["request_sha256"]), r
                assert isinstance(r["image_sha256"], dict)
        assert all(c["canary_id"] == "cn20260924_abcd1234_x1" for c in rt.calls)
        assert all(a["canary_id"] == "none" for a in heart)  # no Astra canary (paid API, not run): explicit none
        assert all(c["image_sha256"].get("cam_head") for c in rt.calls)
        assert all(a["image_sha256"].get("cam_head") for a in heart)
        assert len({c["request_sha256"] for c in rt.calls}) > 1
    assert RuntimeConfig().canary_id == "none" and RuntimeConfig().astra_canary_id == "none"


def test_modular_mock_is_deterministic():
    _, w1, h1 = _run("modular", MockSelector(latency_s=0.30), 8.0)
    _, w2, h2 = _run("modular", MockSelector(latency_s=0.30), 8.0)
    assert [p for _, p, _, _ in h1] == [p for _, p, _, _ in h2]
    np.testing.assert_allclose(w1.tcp, w2.tcp)


def test_fused_mock_interface_holds_and_logs():
    rt, w, hist = _run("fused", MockFusedModel(latency_s=0.30), 3.0)
    s = rt.summary()
    assert s["calls_delivered"] >= 7 and s["chunk"]["played"] > 0
    assert rt.calls[0]["meta"]["privileged_decisions"] is True
    assert s["chunk"]["requested"] >= 8 and s["chunk"]["delivered"] >= 8
    c = rt.chunk_log[-1]
    assert c["latency_s"] == 0.12 and c["t_deliver"] <= 0.33 * c["ds"] + 1e-9  # ready before its step starts


def test_fused_b_check_uses_the_executed_joint_target():
    """(b) for the fused back-end compares the measured joints with the executed chunk target (not skill S's TCP
    command, which the fused path does not execute): a hold chunk on a still world gives no DEVIATE."""
    rt, w, hist = _run("fused", MockFusedModel(latency_s=0.30), 4.0)
    outs = [s.get("prev_outcome") for s in rt.slots_log if s.get("prev_outcome")]
    assert outs and all(o == "OK" for o in outs), outs
    assert rt.ledger.epoch == 0
    s = rt.summary()
    assert s["commit_ratio_mean"] > 0.5 and s["chunk"]["played"] > s["chunk"]["held"]
