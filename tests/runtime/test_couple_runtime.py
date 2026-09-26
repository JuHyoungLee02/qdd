import json

import numpy as np
import pytest

from harvest.couple.cost import PriceTable
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.couple.twolayer import committed_vector
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.fused_action import chunk_value
from harvest.runtime.models import MockFusedModel, MockSelector, ModelResult

from .fakeworld import FakeWorld

FRAME = np.full((12, 16, 3), 60, np.uint8)
NO_FAST = {"contra_steps": 10 ** 6}  # the VLA fast check is Task 7's test; here the offset must run in full


def _run(backend, astra, seconds, params=None, model=None, **cfg_kw):
    """F0 answers (the scripted answers carry no diff); params = extra CoupleParams overrides."""
    if model is None:
        model = MockFusedModel(latency_s=0.30) if backend == "fused" else MockSelector(latency_s=0.30)
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="mock", couple="serial",
                        couple_params={"request_mode": "F0", **(params or {})}, **cfg_kw)
    rt = OursRuntime(cfg, model, astra=astra)
    rt.reset()
    w = FakeWorld()
    hist = []
    for i in range(int(seconds * 100)):
        o = w.obs()
        if i % 10 == 0:
            o["images"] = {c: FRAME for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
        a, meta = rt.act(o)
        w.step(a)
        hist.append((w.t, meta["phase"], w.tcp.copy()))
    return rt, w, hist


def test_serial_continue_completes_pick_and_place_with_one_request_in_flight():
    rt, w, hist = _run("modular", ScriptedCoupleAstra([answer("continue")], latency_s=3.0), 40.0)
    phases = {p for _, p, _ in hist}
    assert {"close", "lift", "carry", "open", "retreat"} <= phases
    s = rt.summary()["couple"]
    assert s["max_inflight"] == 1 and 11 <= s["calls_sent"] <= 15 and s["answers"] >= 11
    assert rt.astra_log == []  # heartbeat off in couple mode
    rt.close()


def _bad_outcomes(rt):
    return sum(1 for e in rt.slots_log if e.get("prev_outcome") in ("DEVIATE", "CONTRADICT"))


def test_offset_does_not_create_false_b_deviations():
    base, _, _ = _run("modular", ScriptedCoupleAstra([answer("continue")], latency_s=3.0), 12.0,
                      params=NO_FAST)
    ed = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.03))
    rt, w, hist = _run("modular", ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0), 12.0,
                       params=NO_FAST)
    s = rt.summary()["couple"]
    assert s["offset"]["applied_m"][2] == pytest.approx(0.03, abs=2e-3)
    assert _bad_outcomes(rt) <= _bad_outcomes(base)  # the shifted reference is what (b) compares with
    jumps = [float(np.linalg.norm(b[2] - a[2])) for a, b in zip(hist, hist[1:])]
    assert max(jumps) <= 0.20 * 0.01 + 0.08 * 0.01 + 1e-9  # skill speed + offset speed per tick
    base.close()
    rt.close()


def test_fresh_misaligned_astra_blocks_the_grasp():
    veto = ScriptedCoupleAstra([answer("continue", intent="misaligned")], latency_s=2.5)
    rt, _, hist = _run("modular", veto, 25.0)
    assert "close" not in {p for _, p, _ in hist}
    s = rt.summary()["couple"]
    assert s["irrev"].get("deny:astra_misaligned", 0) >= 1 and s["events"].get("layer_mismatch", 0) >= 1
    rt.close()
    ok = ScriptedCoupleAstra([answer("continue")], latency_s=2.5)
    rt2, _, hist2 = _run("modular", ok, 25.0)
    assert "close" in {p for _, p, _ in hist2}
    rt2.close()


def test_fused_offset_reaches_the_arm_through_ik():
    ed = answer("edit", execution="failed", dp=(0.0, 0.02, 0.0))
    rt, w, hist = _run("fused", ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0), 12.0,
                       params=NO_FAST)
    assert rt.summary()["couple"]["offset"]["applied_m"][1] == pytest.approx(0.02, abs=2e-3)
    assert w.tcp[1] - hist[0][2][1] == pytest.approx(0.02, abs=5e-3)  # MockFused holds; the bias moves the tip
    base, _, _ = _run("fused", ScriptedCoupleAstra([answer("continue")], latency_s=3.0), 12.0, params=NO_FAST)
    assert _bad_outcomes(rt) <= _bad_outcomes(base)  # the fused half of the Review Focus: no false (b) from the bias
    base.close()
    rt.close()


def test_fused_offset_has_no_jump_when_a_stale_chunk_is_held():
    """Review T10 I2: a held action comes from the last PLAYED chunk, so the offset history is pruned by that chunk's
    observation time (not the current step's stale chunk): no tick moves the tip more than the offset speed."""
    from harvest.couple.driver import TickOut
    rt = OursRuntime(RuntimeConfig(backend="fused", couple="serial", couple_params={"request_mode": "F0"}),
                     MockFusedModel(), astra=ScriptedCoupleAstra([answer("continue")]))
    rt.reset()
    w = FakeWorld()
    kin = w.obs()["kin"]
    dec = {"phase": "continue", "dir_xy": "plus_y"}
    rt.skill.dec, rt.cur_k = dict(dec), 0
    rt.chunks[0] = {"t_state": 0.0, "chunk": np.tile(w.a, (15, 1)), "dt": 1 / 30, "dec": dict(dec)}  # a hold chunk
    rt.chunks[1] = {"t_state": 0.25, "chunk": np.tile(w.a, (15, 1)), "dt": 1 / 30, "dec": {"phase": "hold"}}  # stale
    st = np.r_[0.0, 0.0008, 0.0, 0.0, 0.0, 0.0]  # the offset at its speed cap, v_max x dt
    out = []
    for i in range(80):
        now = round(i * 0.01, 6)
        if i == 40:
            rt.cur_k = 1  # step 1's chunk was conditioned on other decisions -> the last action is held
        rt.couple_out = TickOut(st.copy(), 1.0)
        a = rt._couple_fused(rt._play_chunk(now, w.a), now, kin, w.tcp.copy())
        rt.last_a = a
        w.step(a)
        out.append(a.copy())
    assert rt.chunk_stats["stale_dec"] == 40
    steps = [float(np.max(np.abs(b[:7] - a[:7]))) for a, b in zip(out, out[1:])]
    assert max(steps) <= 0.0008 + 1e-9  # hold chunk: only the offset moves the target
    assert out[-1][1] - out[0][1] == pytest.approx(79 * 0.0008, abs=1e-9)  # no offset step lost or counted twice
    rt.close()


def test_speed_scale_switch_mid_chunk_does_not_jump():
    """Review T10 I1: the chunk play clock runs at speed_scale per tick (lag accrues only while slowed), so a scale
    switch -- also one that spans a chunk switch -- never moves the target more than the chunk's own per-tick motion."""
    from harvest.couple.driver import TickOut
    rt = OursRuntime(RuntimeConfig(backend="fused", couple="serial", couple_params={"request_mode": "F0"}),
                     MockFusedModel(), astra=ScriptedCoupleAstra([answer("continue")]))
    rt.reset()
    dec = {"phase": "continue", "dir_xy": "plus_y"}
    rt.skill.dec, rt.cur_k = dict(dec), 0
    v_row = 0.001  # per 1/30 s row -> 0.0003 per 10 ms tick
    ch0 = np.zeros((30, 8))
    ch0[:, 1] = np.arange(30) * v_row
    rt.chunks[0] = {"t_state": 0.0, "chunk": ch0, "dt": 1 / 30, "dec": dict(dec), "lag": 0.0}
    out = []
    for i in range(60):
        now = round(i * 0.01, 6)
        rt.couple_out = TickOut(np.zeros(6), 0.5 if 10 <= i < 30 else 1.0)
        rt._advance_play_clock(now)
        if i == 20:  # next chunk observed while slowed (its row 0 = the target the arm is at now)
            ch1 = np.zeros((30, 8))
            ch1[:, 1] = chunk_value(ch0, 1 / 30, 0.0, now - rt._play_lag)[1] + np.arange(30) * v_row
            rt.chunks[1] = {"t_state": now, "chunk": ch1, "dt": 1 / 30, "dec": dict(dec), "lag": rt._play_lag}
        if i == 35:
            rt.cur_k = 1
        out.append(rt._play_chunk(now, np.zeros(8)))
    steps = [float(np.max(np.abs(b[:7] - a[:7]))) for a, b in zip(out, out[1:])]
    assert max(steps) <= v_row * 30 * 0.01 + 1e-12
    assert min(steps[12:28]) < 0.6 * v_row * 30 * 0.01  # it did slow down
    rt.close()


def test_chunk_vec_error_never_stops_the_run():
    class _BadKin(FakeWorld):
        def obs(self):
            o = super().obs()
            k = o["kin"]

            def fk_pos(q):
                raise RuntimeError("no physx view")
            k.fk_pos = fk_pos
            return o
    model = _MovingFused()
    cfg = RuntimeConfig(backend="fused", couple="serial", couple_params={"request_mode": "F0"})
    rt = OursRuntime(cfg, model, astra=ScriptedCoupleAstra([answer("continue")], latency_s=3.0))
    rt.reset()
    w = _BadKin()
    for _ in range(300):
        a, _ = rt.act(w.obs())
        w.step(a)
    errs = [e for e in rt.events if e.get("event") == "couple_chunk_vec_error"]
    assert len(errs) == 1 and "no physx view" in errs[0]["error"]
    assert all(r["src"] == "decision" for r in rt.driver.log if r["type"] == "adherence")
    rt.close()


def test_couple_guards_paid_client_and_k3():
    class _PaidLike:
        model = "gpt-6-astra"
    with pytest.raises(ValueError, match="couple_prices"):  # astra_mode says mock but the client is not a mock
        OursRuntime(RuntimeConfig(couple="serial", astra_mode="mock"), MockSelector(), astra=_PaidLike())
    OursRuntime(RuntimeConfig(couple="serial", astra_mode="mock"), MockSelector(),
                astra=ScriptedCoupleAstra([])).close()  # mock: ok
    with pytest.raises(ValueError, match="K3"):
        OursRuntime(RuntimeConfig(couple="serial", hb_mode="K3"), MockSelector(), astra=ScriptedCoupleAstra([]))


def test_sidecar_couple_rows_include_driver_events():
    from harvest.runtime.ir_policy import _couple_rows
    veto = ScriptedCoupleAstra([answer("continue", intent="misaligned")], latency_s=2.5)
    rt, _, _ = _run("modular", veto, 25.0)
    rows = _couple_rows(rt)
    kinds = {r["couple_kind"] for r in rows}
    assert {"send", "answer", "event"} <= kinds
    assert any(r["couple_kind"] == "event" and r["event"] == "layer_mismatch" for r in rows)
    assert all("type" not in r for r in rows)
    rt.close()


def test_reset_with_request_in_flight_charges_and_forgets_it(tmp_path):
    f = tmp_path / "prices.json"
    f.write_text('{"model": "test", "date": "2026-09-26", "usd_per_mtok_input": 2.0, "usd_per_mtok_cached_input": 0.5,'
                 ' "usd_per_mtok_output": 8.0, "krw_per_usd": 1400.0, "source": "unit test"}')
    led = str(tmp_path / "ledger.jsonl")
    ast = ScriptedCoupleAstra([answer("edit", execution="failed", dp=(0.0, 0.0, 0.02))], latency_s=3.0,
                              usage={"input_tokens": 3000, "output_tokens": 900})
    rt, w, _ = _run("modular", ast, 1.0, couple_prices=str(f), couple_budget_krw=1000.0, couple_ledger=led)
    assert list(rt.couple_ledger.reserved) == ["e1:1"]
    rt.reset()
    assert rt.couple_ledger.reserved == {} and rt.episode == 2
    kinds = [json.loads(x)["kind"] for x in open(led, encoding="utf-8")]
    assert kinds == ["unanswered"]
    for _ in range(200):
        a, _ = rt.act(w.obs())
        w.step(a)
    s = rt.summary()["couple"]
    assert s["offset"]["applied_m"] == [0.0, 0.0, 0.0] and s["answers"] == 0
    for _ in range(200):  # past the old answer's due time (sent at t=0, 3.0 s) and the new one's (sent at t=1, 4.0 s)
        a, _ = rt.act(w.obs())
        w.step(a)
    ans = [r for r in rt.driver.log if r["type"] == "answer"]
    assert [r["t_state"] for r in ans] == [1.0]  # only episode 2's own request; the old one never arrives
    rows = [json.loads(x) for x in open(led, encoding="utf-8")]
    assert [(r["key"], r["kind"]) for r in rows] == [("e1:1", "unanswered"), ("e2:1", "charge")]
    rt.close()


def test_paid_couple_mode_needs_prices_budget_and_ledger():
    with pytest.raises(ValueError, match="couple_prices"):
        OursRuntime(RuntimeConfig(couple="serial", astra_mode="api"), MockSelector(), astra=ScriptedCoupleAstra([]))
    with pytest.raises(ValueError, match="off \\| serial"):
        OursRuntime(RuntimeConfig(couple="stagger"), MockSelector())
    assert PriceTable.free().is_free


class _MovingFused(MockFusedModel):
    """A fused mock whose chunk moves the tip along its committed decision (FakeWorld: the first three joints are the
    TCP), so the chunk's executed TCP displacement is defined (controller ruling C3, canon §84 supplements 4-5)."""

    def chunk(self, ctx, committed):
        r = super().chunk(ctx, committed)
        v = committed_vector(committed)
        if v is not None:
            step = np.zeros(8)
            step[:3] = v / np.linalg.norm(v) * 0.001
            r = ModelResult({}, r.latency_s, call_id=r.call_id, chunk=r.chunk + np.arange(self.H)[:, None] * step,
                            chunk_dt=r.chunk_dt, meta=r.meta)
        return r


def test_adherence_uses_the_executed_chunk_on_fused_and_the_decision_on_modular():
    rt, _, _ = _run("fused", ScriptedCoupleAstra([answer("continue")], latency_s=3.0), 6.0, model=_MovingFused())
    adh = [r for r in rt.driver.log if r["type"] == "adherence"]
    assert rt.driver.summary()["adherence"]["chunk_vs_decision"]["n"] > 0  # chunk-level rows were logged
    assert adh and {r["src"] for r in adh} == {"chunk"}
    rt.close()
    ed = answer("edit", execution="failed", dp=(0.0, 0.0, 0.03))
    rt2, _, _ = _run("modular", ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0), 12.0,
                     params=NO_FAST)
    adh2 = [r for r in rt2.driver.log if r["type"] == "adherence"]
    assert adh2 and {r["src"] for r in adh2} == {"decision"}
    assert rt2.driver.summary()["adherence"]["chunk_vs_decision"]["n"] == 0
    rt2.close()
