"""Plan 2026-09-26 final whole-branch review, controller ruling FF: I1 (hold-play hides the executed motion from the
coupling), I2 (hold-play lets the fused chunk's gripper act during a T1-CONTRADICT hold), I3 (paid guard for every
real Astra client, heartbeat included). Kinematic fake world + mock models only; no network, no paid call."""
from dataclasses import asdict

import numpy as np
import pytest

from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.runtime.conditions import condition
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.m4 import M4Params
from harvest.runtime.models import MockFusedModel, MockSelector, ModelResult

from .fakeworld import FakeWorld

FRAME = np.full((12, 16, 3), 60, np.uint8)


def _world():
    """FakeWorld with the pads starting at 78 mm (the stuck approach width, vla_alone_diag.md 1): T1 'open' is False
    from the first tick (no hysteresis), so the first approach step check contradicts -> M4 hold; no 107 -> 78 mm
    close transition exists for the coupling gate to veto."""
    w = FakeWorld()
    w.width, w.a[7] = 0.078, 0.078
    return w


class _Held(MockFusedModel):
    """Approach chunk at 78 mm (below the 80.5 mm T1 'open' threshold without hysteresis -> CONTRADICT -> M4 hold),
    moving the TCP dx per row; a chunk requested while held (committed {}) sets the width `held_w`."""

    def __init__(self, dx=0.0005, held_w=0.078, **kw):
        super().__init__(**kw)
        self.dx, self.held_w = dx, held_w

    def chunk(self, ctx, committed):
        r = super().chunk(ctx, committed)
        c = r.chunk.copy()
        c[:, 7] = 0.078 if committed else self.held_w
        c[:, 0] += self.dx * np.arange(len(c))
        return ModelResult({}, r.latency_s, call_id=r.call_id, chunk=c, chunk_dt=r.chunk_dt, meta=r.meta)


def _run(model, seconds, astra=None, t1=None, **over):
    cond = "C5"
    m4 = {**asdict(M4Params()), **condition(cond)[0]}
    cfg = RuntimeConfig(backend="fused", clock="simlat", condition=cond, m4=m4, grip_open_leave_m=None, **over)
    rt = OursRuntime(cfg, model, astra=astra)
    rt.reset()
    if t1 is not None:  # the gripper gate's T1 premise, pinned (the M4 (b) check keeps the measured T1)
        base = rt._t1
        rt._t1 = lambda: {**base(), **t1}
    w, acts = _world(), []
    for i in range(int(round(seconds * 100))):
        o = w.obs()
        if astra is not None and i % 10 == 0:
            o["images"] = {c: FRAME for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
        a, _ = rt.act(o)
        w.step(a)
        acts.append(np.asarray(a, float).copy())
    return rt, w, np.array(acts)


# ------------------------------------------------------------------------------------------------ I1
def test_hold_play_chunk_vector_reaches_the_coupling():
    """I1: while held (dec = {}) the step's chunk is still played (hold_played); the coupling must see that executed
    motion: chunk_vec non-None on held steps, arrow source chunk, prediction != tip now, vla_chunks counted."""
    seen = []
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=1.0)
    m4 = {**asdict(M4Params()), **condition("C5")[0]}
    cfg = RuntimeConfig(backend="fused", clock="simlat", condition="C5", m4=m4, grip_open_leave_m=None,
                        hold_timeout_s=None, couple="serial",
                        couple_params={"request_mode": "F0", "contra_steps": 10 ** 6, "reconcile_apply": False})
    rt = OursRuntime(cfg, _Held(), astra=ast)
    rt.reset()
    on_step = rt.driver.on_step

    def spy(committed, outcome, now, chunk_vec=None):
        seen.append((now, rt.hold_step, chunk_vec))
        return on_step(committed, outcome, now, chunk_vec=chunk_vec)
    rt.driver.on_step = spy
    w = _world()
    for i in range(600):
        o = w.obs()
        if i % 10 == 0:
            o["images"] = {c: FRAME for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
        a, _ = rt.act(o)
        w.step(a)
    assert rt.chunk_stats["hold_played"] > 0
    held = [(t, v) for t, h, v in seen if h]
    assert len(held) >= 5
    assert all(v is not None and v[0] > 0.001 for _, v in held[1:])  # the chunk's dx motion, not None
    t_held0 = held[1][0]
    reqs = [c["req"] for c in ast.calls if c["req"]["t_state"] > t_held0 + 0.34]
    assert reqs
    for r in reqs:
        assert r["vla_now"]["arrow_src"] == "chunk" and r["vla_now"]["next_motion_m"] is not None
        assert r["predicted_ee_at_arrival"]["pos_m"] != r["tip_now_m"]
    assert sum(1 for _, c in rt.driver._exec if c) >= len(held) - 1
    rt.close()


# ------------------------------------------------------------------------------------------------ I2
def test_hold_play_keeps_the_gripper_without_the_t1_premise_coupling_off():
    """I2: fused, coupling off, forced hold; the held chunk closes the gripper (78 -> 40 mm) but T1 says not open
    (78 mm < 80.5 mm): no close premise -> the gripper stays at the last command while held / escaping."""
    rt, w, A = _run(_Held(held_w=0.04), 8.0)
    assert rt.chunk_stats["hold_played"] > 0 and rt.driver is None
    assert A[:, 7].min() >= 0.078 - 1e-9
    assert rt.chunk_stats["hold_grip_kept"] > 0


def test_hold_play_gripper_proceeds_with_the_t1_premise(monkeypatch):
    """I2: the same hold with the close premise (gripper open + near) true -> the chunk's close proceeds (at the
    unchanged rate limiter)."""
    monkeypatch.setattr("harvest.runtime.core.near_contact", lambda raw, phase: True)
    rt, w, A = _run(_Held(held_w=0.04), 8.0, t1={"gripper_open": True})
    assert rt.chunk_stats["hold_played"] > 0
    assert A[:, 7].min() <= 0.04 + 1e-9


def test_hold_play_gripper_gate_also_applies_with_coupling_on():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=1.0)
    rt, w, A = _run(_Held(held_w=0.04), 8.0, astra=ast, couple="serial",
                    couple_params={"request_mode": "F0", "reconcile_apply": False})
    assert rt.chunk_stats["hold_played"] > 0 and A[:, 7].min() >= 0.078 - 1e-9
    rt.close()


# ------------------------------------------------------------------------------------------------ I3
class _PaidLike:
    model = "gpt-6-astra"


def test_real_astra_client_needs_approval_for_the_heartbeat():
    with pytest.raises(ValueError, match="approval"):
        OursRuntime(RuntimeConfig(astra_mode="api"), MockSelector(), astra=_PaidLike())
    with pytest.raises(ValueError, match="approval"):  # astra_mode says mock, the client is not a mock
        OursRuntime(RuntimeConfig(astra_mode="mock"), MockSelector(), astra=_PaidLike())
    OursRuntime(RuntimeConfig(astra_mode="api", astra_approval="user approval: user-log 114, test"), MockSelector(),
                astra=_PaidLike()).close()


def test_real_astra_client_needs_approval_for_the_coupling(tmp_path):
    f = tmp_path / "prices.json"
    f.write_text('{"model": "test", "date": "2026-09-26", "usd_per_mtok_input": 2.0, "usd_per_mtok_cached_input": 0.5,'
                 ' "usd_per_mtok_output": 8.0, "krw_per_usd": 1400.0, "source": "unit test"}')
    kw = dict(couple="serial", couple_prices=str(f), couple_budget_krw=100.0, couple_ledger=str(tmp_path / "l.jsonl"))
    with pytest.raises(ValueError, match="approval"):
        OursRuntime(RuntimeConfig(astra_mode="api", **kw), MockSelector(), astra=_PaidLike())
    OursRuntime(RuntimeConfig(astra_mode="api", astra_approval="user approval: test", **kw), MockSelector(),
                astra=_PaidLike()).close()


def test_mock_and_local_clients_need_no_approval():
    from harvest.runtime.astra_hb import MockAstra

    class _Local:
        model = "local:qwen"
    OursRuntime(RuntimeConfig(), MockSelector(), astra=MockAstra(1.0)).close()
    OursRuntime(RuntimeConfig(couple="serial"), MockSelector(), astra=ScriptedCoupleAstra([])).close()
    OursRuntime(RuntimeConfig(couple="serial"), MockSelector(), astra=_Local()).close()
    OursRuntime(RuntimeConfig(astra_mode="none"), MockSelector()).close()
