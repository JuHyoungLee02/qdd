"""Plan 2026-09-26 Task 25 (E-VLA-solo Q3, docs/stage3/results/vla_alone_diag.md, vla_solo.md): the C5 runtime
deadlock (T1 contradiction -> M4 hold -> decisions emptied -> the only chunk dropped as stale -> the same contradiction)
and the fused chunk-transition joint jumps (> 0.04 rad per tick). Kinematic fake world + mock fused models only."""
from dataclasses import asdict

import numpy as np

from harvest.runtime.conditions import condition
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.m4 import M4Params
from harvest.runtime.measure import ProprioRules, measure, values, VerifyCal
from harvest.runtime.models import MockFusedModel, ModelResult

from .fakeworld import HM, TZ, FakeWorld

T_C = 0.33


class _ChunkEdit(MockFusedModel):
    """MockFusedModel (hold the current joints, 15 rows at 30 Hz) with an edit hook on the chunk rows."""

    def edit(self, c, ctx):
        return c

    def chunk(self, ctx, committed):
        r = super().chunk(ctx, committed)
        c = self.edit(r.chunk.copy(), ctx)
        return ModelResult({}, r.latency_s, call_id=r.call_id, chunk=c, chunk_dt=r.chunk_dt, meta=r.meta)


class _NarrowGrip(_ChunkEdit):
    """The approach chunk's gripper width 78 mm: just under the 80.5 mm T1 'open' threshold (vla_alone_diag.md ①:
    77.1 / 78.1 / 80.2 mm in the three stuck approach episodes); dx per row moves the TCP (joint 0 = x here)."""

    def __init__(self, width=0.078, dx=0.0, **kw):
        super().__init__(**kw)
        self.width, self.dx = width, dx

    def edit(self, c, ctx):
        c[:, 7] = self.width
        c[:, 0] += self.dx * np.arange(len(c))
        return c


class _Switch(_ChunkEdit):
    """Joint 4 at 0.3 rad on odd steps and 0 on even ones (a 0.3 rad discontinuity at every chunk switch); the
    gripper optionally steps 107 -> 30 mm between two chunks (from step 6 on)."""

    def __init__(self, grip=False, **kw):
        super().__init__(**kw)
        self.grip = grip

    def edit(self, c, ctx):
        c[:, 4] = 0.3 * (ctx["ds"] % 2)
        if self.grip:
            c[:, 7] = 0.03 if ctx["ds"] >= 6 else 0.107
        return c


class _Ramp(_ChunkEdit):
    """A smooth chunk: x += 0.3 mm per row from the current joints (per tick far below 0.04 rad)."""

    def edit(self, c, ctx):
        c[:, 0] += 0.0003 * np.arange(len(c))
        return c


class _Lift(_ChunkEdit):
    """Keeps the gripper closed (40 mm command) and lifts the TCP 3 mm per row (joint 2 = z here)."""

    def edit(self, c, ctx):
        c[:, 7] = 0.04
        c[:, 2] += 0.003 * np.arange(len(c))
        return c


class _SlipWorld(FakeWorld):
    """The mug starts between the closed pads (held, effort 5); the pad force drops to 0 at t_slip while the pads
    stay on the mug (vla_alone_diag.md ②: width 58-77 mm, force under the 1.14 holding threshold)."""

    def __init__(self, t_slip, drop=False):
        super().__init__()
        self.t_slip, self.drop = t_slip, drop
        self.tcp = np.array([self.mug[0], self.mug[1], TZ + self.mug[2] + HM - 0.018])
        self.width = 0.04
        self.a = np.r_[self.tcp, 0, 0, 0, 0, self.width]

    def m1(self):
        if self.drop and self.held and self.t >= self.t_slip - 1e-9:
            # drop: the mug falls away from the pads, which close past it (measured gap = the commanded 40 mm)
            self.held, self.mug = False, np.array([0.30, -0.35, HM])
        o = super().m1()
        if self.t >= self.t_slip - 1e-9:
            o["raw"]["grip"]["effort"] = 0.0
        return o


def _run(model, seconds, world=None, cond="C5", astra=None, **over):
    m4 = {**asdict(M4Params()), **condition(cond)[0]}
    cfg = RuntimeConfig(backend="fused", clock="simlat", condition=cond, m4=m4, **over)
    rt = OursRuntime(cfg, model, astra=astra)
    rt.reset()
    w = world or FakeWorld()
    acts, tcps = [], []
    for i in range(int(round(seconds * 100))):
        o = w.obs()
        if astra is not None and i % 10 == 0:
            o["images"] = {c: np.full((12, 16, 3), 60, np.uint8) for c in ("cam_head", "cam_wrist_left",
                                                                            "cam_wrist_right")}
        a, _ = rt.act(o)
        w.step(a)
        acts.append(np.asarray(a, float).copy())
        tcps.append(w.tcp.copy())
    rt.close()
    return rt, w, np.array(acts), np.array(tcps)


def _hold_runs(rt):
    """Continuous M4 hold runs in seconds (a run: first held step start -> the next unheld step start / episode end)."""
    runs, t0 = [], None
    for e in rt.slots_log:
        if e["hold"] and t0 is None:
            t0 = e["t"]
        elif not e["hold"] and t0 is not None:
            runs.append(e["t"] - t0)
            t0 = None
    if t0 is not None:
        runs.append(rt.t_last - t0)
    return runs


# ---------------------------------------------------------------------------------------------- A. deadlock
def test_the_deadlock_loop_reproduces_with_the_three_fixes_off():
    """Before the fix (hysteresis off, no escape, the stale chunk dropped while holding): the first T1 contradiction
    holds to the episode end (vla_solo.md Q3: permanent hold 8/12), every chunk after it is dropped as stale."""
    rt, w, A, _ = _run(_NarrowGrip(), 10.0, grip_open_leave_m=None, hold_timeout_s=None, hold_play_chunk=False)
    holds = [e["hold"] for e in rt.slots_log]
    first = holds.index(True)
    assert first * T_C < 2.0 and all(holds[first:])  # permanent
    assert rt.chunk_stats["stale_dec"] > 0 and rt.chunk_stats.get("hold_played", 0) == 0
    assert not any(e["event"] == "hold_escape" for e in rt.events)
    assert all(e.get("t1_check") == ["gripper_open"] for e in rt.slots_log[first + 1:])


def test_gripper_open_hysteresis_keeps_a_78mm_approach_chunk_open():
    rt, w, A, _ = _run(_NarrowGrip(), 10.0)  # defaults: leave 75 mm
    assert abs(w.width - 0.078) < 1e-9  # the chunk width was reached (inside the 75-80.5 mm band)
    assert rt.measure_stats["t1_contradict"] == 0 and not any(e["hold"] for e in rt.slots_log)
    assert rt._t1()["gripper_open"] is True


def test_proprio_rule_hysteresis_enter_leave_and_holding():
    r = ProprioRules(th_w_leave=0.075)
    assert r.eval(0.078, 0.0, 0.2, prev_open=True)["gripper_open"] is True  # stays open inside the band
    assert r.eval(0.078, 0.0, 0.2, prev_open=False)["gripper_open"] is False  # entering needs >= 80.5 mm
    assert r.eval(0.0806, 0.0, 0.2, prev_open=False)["gripper_open"] is True
    assert r.eval(0.0749, 0.0, 0.2, prev_open=True)["gripper_open"] is False  # left below 75 mm
    held = r.eval(0.078, 5.0, 0.2, prev_open=True)
    assert held["holding_t"] is True and held["gripper_open"] is False  # holding is never 'open'
    old = ProprioRules()  # no leave value: the registered E-M4b-meas rule, unchanged
    assert old.eval(0.078, 0.0, 0.2, prev_open=True)["gripper_open"] is False
    cal = VerifyCal.default()
    assert values(measure({"width": 0.078, "grip_effort": 0.0, "tcp_z": 0.2, "prev_open": True}, None, cal,
                          r))["gripper_open"] is True
    assert values(measure({"width": 0.078, "grip_effort": 0.0, "tcp_z": 0.2}, None, cal, r))["gripper_open"] is False


def test_hold_escape_bounds_every_hold_and_logs_it():
    """Hysteresis off so the contradiction persists: each hold ends within hold_timeout_s + one step."""
    rt, w, A, _ = _run(_NarrowGrip(), 12.0, grip_open_leave_m=None)
    runs = _hold_runs(rt)
    assert runs and max(runs) <= 3.0 + T_C + 0.02, runs
    esc = [e for e in rt.events if e["event"] == "hold_escape"]
    assert len(esc) >= 2
    assert all(e["held_s"] >= 3.0 - 1e-9 and e["t1_false"] == ["gripper_open"] for e in esc)
    s = rt.summary()
    assert s["hold"]["escapes"] == len(esc) and s["hold"]["max_s"] <= 3.0 + T_C + 0.02
    assert s["hold"]["timeout_s"] == 3.0


def test_the_escape_step_plays_its_chunk():
    """Fix F25 I1: the escape step's chunk was requested during the hold (reopened slots -> committed {}), so its
    decisions never match the escape step's; it is played by the hold-play fallback, not dropped as stale."""
    rt, *_ = _run(_NarrowGrip(dx=0.0005), 12.0, grip_open_leave_m=None)
    esc = [e for e in rt.slots_log if e.get("hold_escape")]
    assert esc and all(e["decisions"] and not e["hold"] for e in esc)
    assert rt.chunk_stats["escape_played"] >= 33  # at least one whole escape step (~33 ticks) played its chunk
    off = _run(_NarrowGrip(dx=0.0005), 12.0, grip_open_leave_m=None, hold_play_chunk=False)[0]
    assert off.chunk_stats["escape_played"] == 0


def test_repeated_escapes_escalate_and_the_held_time_is_reported():
    """Fix F25 I2: 3 escapes with no non-hold step between -> hold_stuck event + fail path (mode hold_stuck), the
    streak restarts; summary hold.total_s / frac = the held time (analysis replaces 'permanent hold')."""
    rt, *_ = _run(_NarrowGrip(), 30.0, grip_open_leave_m=None)
    esc = [e for e in rt.events if e["event"] == "hold_escape"]
    assert [e["streak"] for e in esc][:6] == [1, 2, 3, 1, 2, 3]
    stuck = [e for e in rt.events if e["event"] == "hold_stuck"]
    assert len(stuck) == len(esc) // 3 >= 2 and all(s["escapes"] == 3 for s in stuck)
    fp = [e for e in rt.events if e.get("event") == "fail_path" and e["sig"]["mode"] == "hold_stuck"]
    assert len(fp) == len(stuck) and all(e["sig"]["evidence"] == "m4_hold" for e in fp)
    h = rt.summary()["hold"]
    assert h["stuck"] == len(stuck) and h["escape_cap"] == 3
    assert abs(h["total_s"] - sum(_hold_runs(rt))) < 0.02 and 0.5 < h["frac"] < 1.0
    none = _run(_NarrowGrip(), 10.0)[0].summary()["hold"]  # hysteresis on: nothing held
    assert none["total_s"] == 0.0 and none["frac"] == 0.0 and none["stuck"] == 0


def test_holding_plays_the_current_chunk_instead_of_dropping_it():
    """While held, the step's chunk is played (not dropped as stale): the arm keeps following the VLA."""
    on = _run(_NarrowGrip(dx=0.0005), 6.0, grip_open_leave_m=None, hold_timeout_s=None)
    off = _run(_NarrowGrip(dx=0.0005), 6.0, grip_open_leave_m=None, hold_timeout_s=None, hold_play_chunk=False)
    for rt, *_ in (on, off):
        assert any(e["hold"] for e in rt.slots_log)
    rt_on, _, _, tcp_on = on
    rt_off, _, _, tcp_off = off
    assert rt_on.chunk_stats["hold_played"] > 0
    assert rt_off.chunk_stats["hold_played"] == 0 and rt_off.chunk_stats["stale_dec"] > 0
    i = int(round(rt_off.slots_log[[e["hold"] for e in rt_off.slots_log].index(True)]["t"] * 100)) + 60
    assert np.allclose(tcp_off[i:], tcp_off[i])  # frozen: the old hold
    assert tcp_on[-1][0] - tcp_on[i][0] > 0.01  # moving with the chunks


def test_pads_closed_past_after_lift_take_the_fail_path():
    """The VLA closed the gripper itself (skill cmd_w stays open on the fused path); the mug drops and the pads close
    past it (40 mm < 50.1 mm) in lift -> object_lost (skill) -> T_fail stand-in (_fail_event), phase back to
    approach -- not a silent lift."""
    rt, w, A, _ = _run(_Lift(), 4.0, world=_SlipWorld(t_slip=1.5, drop=True))
    ph = [e for e in rt.events if e.get("event") == "phase"]
    assert any(e["to"] == "lift" for e in ph)
    lost = [e for e in rt.events if e.get("event") == "object_lost"]
    assert len(lost) == 1 and lost[0]["t"] >= 1.49 + 0.15 - 1e-9  # 0.15 s holding debounce after the last hold
    fp = [e for e in rt.events if e.get("event") == "fail_path" and e["sig"]["mode"] == "object_lost"]
    assert len(fp) == 1
    assert any(e["to"] == "approach" and e["why"] == "object_lost" for e in ph)
    assert not any(e.get("event") == "grip_force_low" for e in rt.events)


def test_force_only_grip_loss_on_a_carried_mug_is_logged_not_object_lost():
    """Fix F25 I3: pad force 0 with the pads still on the mug (64 mm, diag ② 58-77 mm) -> one grip_force_low event,
    no object_lost / fail path from the skill, the phase stays lift."""
    rt, w, A, _ = _run(_Lift(), 4.0, world=_SlipWorld(t_slip=1.5))
    assert not any(e.get("event") == "object_lost" for e in rt.events)
    low = [e for e in rt.events if e.get("event") == "grip_force_low"]
    assert len(low) == 1 and low[0]["phase"] == "lift" and abs(low[0]["w"] - 0.064) < 1e-9
    assert not any(e.get("event") == "fail_path" and e["sig"]["mode"] == "object_lost" for e in rt.events)
    assert rt.skill.phase == "lift" and w.held


def test_c3_is_unchanged_by_the_escape_and_the_hold_play():
    """C3 has no (b) hold: the escape and the hold-play never fire and the actions are byte-identical."""
    a = _run(_NarrowGrip(dx=0.0003), 6.0, cond="C3", grip_open_leave_m=None)
    b = _run(_NarrowGrip(dx=0.0003), 6.0, cond="C3", grip_open_leave_m=None, hold_timeout_s=None,
             hold_play_chunk=False)
    assert a[2].tobytes() == b[2].tobytes()
    assert not any(e["hold"] for e in a[0].slots_log)
    assert a[0].summary()["hold"]["escapes"] == 0 and a[0].chunk_stats["hold_played"] == 0


# ---------------------------------------------------------------------------------------------- B. blending
def test_chunk_switch_discontinuity_is_blended_to_004_rad_per_tick():
    rt, w, A, _ = _run(_Switch(), 6.0)
    d = np.abs(np.diff(A[:, :7], axis=0))
    assert d.max() < 0.04  # tools/vla_alone/analyze_vla.py counts |delta| > 0.04 as a jump tick
    f32 = np.abs(np.diff(A[:, :7].astype(np.float32), axis=0))
    assert f32.max() <= np.float32(0.04)  # fix F25 M7: the margin survives float32 logging
    assert A[:, 4].max() >= 0.3 - 1e-9  # the blend catches up with the new chunk
    assert rt.chunk_stats["blend_arm"] > 0
    raw = _run(_Switch(), 6.0, blend_max_dq=None)[2]
    assert np.abs(np.diff(raw[:, :7], axis=0)).max() >= 0.29  # the discontinuity exists without the blend


def test_gripper_jump_at_a_chunk_switch_uses_the_task17_catch_rate():
    rt, w, A, _ = _run(_Switch(grip=True), 6.0)
    dw = np.abs(np.diff(A[:, 7]))
    assert dw.max() <= 0.077 * 0.01 / 0.5 + 1e-9  # own rate 0 + gap / one chunk horizon (0.5 s) per 10 ms tick
    assert A[:, 7].min() <= 0.03 + 1e-9 and rt.chunk_stats["blend_grip"] > 0
    raw = _run(_Switch(grip=True), 6.0, blend_max_dq=None)[2]
    assert np.abs(np.diff(raw[:, 7])).max() >= 0.07


def test_couple_mode_offset_bias_with_a_chunk_switch_is_blended(monkeypatch):
    """Fix F25 M8: coupling on (driver present, Astra y-edits at authority 1 -> joint bias via IK) with a 0.3 rad
    chunk switch: every tick stays under 0.04 rad and the offset still reaches the arm."""
    from harvest.couple.mock import ScriptedCoupleAstra, answer
    monkeypatch.setattr("harvest.train.sr1c_authority.Hysteresis.step", lambda self, d, phase, contact=False: 1.0)
    ed = answer("edit", execution="failed", dp=(0.0, 0.02, 0.0))
    params = {"request_mode": "F0", "contra_steps": 10 ** 6, "reconcile_apply": False}
    rt, w, A, _ = _run(_Switch(), 12.0, astra=ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0),
                       couple="serial", couple_params=params)
    assert rt.driver is not None and rt.chunk_stats["blend_arm"] > 0
    assert rt.summary()["couple"]["offset"]["applied_m"][1] > 0.01
    assert np.abs(np.diff(A[:, :7], axis=0)).max() < 0.04
    assert A[:, 1].max() - A[0, 1] > 0.01  # the y bias moved the arm (joint 1 = y in the fake kinematics)
    rt.close()


def test_blending_is_a_no_op_on_a_smooth_chunk_sequence():
    on = _run(_Ramp(), 6.0)
    off = _run(_Ramp(), 6.0, blend_max_dq=None)
    assert on[0].chunk_stats["played"] > 100
    assert on[2].tobytes() == off[2].tobytes()
    assert on[0].chunk_stats["blend_arm"] == 0 and on[0].chunk_stats["blend_grip"] == 0
