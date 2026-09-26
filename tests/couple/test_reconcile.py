"""Canon §91 arrival reconciliation and the chunk-based predicted state (plan 2026-09-26 Task 19, controller rulings
N2 / R19): one verdict per valid delivered answer (done / valid / changed / conflict) from synthetic tip / phase / gripper
traces, the precedence with the stale age (> stale_edit_s), a = 0 applies nothing, the next request's
since_last_request context, the predicted point near a stop (no 6-9 cm jump, book 02 P113)."""
import numpy as np
import pytest

from harvest.couple.cost import CostLedger, PriceTable
from harvest.couple.driver import CoupleDriver, TickView
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.couple.params import CoupleParams
from harvest.couple.reconcile import VERDICTS, classify

from .test_driver import CAMS, FR, MiniQueue

SMALL_X = {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"}
EDIT_Z = dict(execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.02))
P0 = np.array([1.0, 0.0, 0.0])


def _loop(astra, seconds, p=None, phase=lambda now: "approach", auth=lambda now: None, tip=lambda now: P0,
          t1=lambda now: {}, step=None, backend=None):
    p = p or CoupleParams()
    q = MiniQueue()
    drv = CoupleDriver(p, astra, CostLedger(None, 0.0, PriceTable.free()), q.submit, "Put the red mug on the tray.",
                       backend=backend)
    steps = []
    for i in range(int(round(seconds * 100))):
        now = round(i * 0.01, 6)
        for r in q.due(now):
            drv.on_delivery(r, now, t1(now))
        if step is not None and i % 33 == 0:
            step(drv, now)
        out = drv.tick(TickView(now=now, dt=0.01, tcp_p=np.asarray(tip(now), float), phase=phase(now), stage="S1",
                                near=False, committed=SMALL_X, frames=FR, cams=CAMS, t1=t1(now),
                                authority=auth(now)))
        steps.append(out.step6)
    return drv, np.array(steps)


def _rec(drv):
    return [r for r in drv.log if r["type"] == "reconcile"]


def _ramp(vec, t0=0.5, t1=2.5):
    """VLA tip motion: P0 until t0, linear to P0 + vec at t1, then still."""
    vec = np.asarray(vec, float)
    return lambda now: P0 + vec * min(1.0, max(0.0, (now - t0) / (t1 - t0)))


# ------------------------------------------------------------------ pure classification
def _cls(**kw):
    base = dict(command="edit", edit_dp=(0.0, 0.0, 0.02), edit_gripper="keep", plan_do="none",
                vla_motion=(0.0, 0.0, 0.0), phase0="approach", phase1="approach", grip0={}, grip1={}, age=3.0,
                p=CoupleParams())
    base.update(kw)
    return classify(**base)


def test_classify_each_verdict_and_the_precedence():
    assert _cls()["verdict"] == "valid" and _cls()["reason"] == "still" and _cls()["factor"] == 1.0
    d = _cls(vla_motion=(0.0, 0.0, 0.017))
    assert d["verdict"] == "done" and d["frac_done"] == pytest.approx(0.85) and d["factor"] == pytest.approx(0.15)
    assert _cls(vla_motion=(0.0, 0.0, 0.03))["factor"] == 0.0  # >= 1: skipped
    assert _cls(vla_motion=(0.0, 0.0, -0.02))["verdict"] == "conflict"
    assert _cls(vla_motion=(0.0, 0.0, -0.005))["verdict"] == "valid"  # < recon_still_m: no conflict evidence
    assert _cls(phase1="descend")["verdict"] == "changed" and _cls(phase1="descend")["reason"] == "segment"
    g = _cls(grip0={"holding_t": False}, grip1={"holding_t": True})
    assert (g["verdict"], g["reason"]) == ("changed", "gripper")
    ad = _cls(edit_gripper="close", grip0={"gripper_open": True}, grip1={"gripper_open": False})
    assert (ad["verdict"], ad["reason"], ad["factor"]) == ("done", "action_done", 0.0)
    pl = _cls(command="continue", edit_dp=None, plan_do="open", grip0={"gripper_open": False},
              grip1={"gripper_open": True})
    assert (pl["verdict"], pl["reason"]) == ("done", "action_done")
    mv = _cls(vla_motion=(0.03, 0.0, 0.0))  # moved sideways in the same segment: still a valid correction
    assert (mv["verdict"], mv["reason"]) == ("valid", "moving")
    # stale (age > 15 s): changed unless the valid-still conditions hold
    assert _cls(age=16.0)["verdict"] == "valid"
    st = _cls(age=16.0, vla_motion=(0.03, 0.0, 0.0))
    assert (st["verdict"], st["reason"]) == ("changed", "stale")
    assert _cls(age=16.0, vla_motion=(0.0, 0.0, -0.02))["reason"] == "stale"  # stale before conflict
    assert _cls(age=16.0, phase1="descend")["reason"] == "segment"  # segment before stale
    # action_done before segment change (the grasp happened: the plan / edit is done, not merely outdated)
    assert _cls(edit_gripper="close", phase1="close", grip0={"gripper_open": True},
                grip1={"gripper_open": False})["reason"] == "action_done"
    assert set(VERDICTS) == {"done", "valid", "changed", "conflict"}


# ------------------------------------------------------------------ in the driver
def test_valid_still_applies_the_edit_at_single_weight():
    drv, steps = _loop(ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0), 6.5)
    r = _rec(drv)[0]
    assert (r["verdict"], r["reason"], r["no"]) == ("valid", "still", 1) and r["eat_candidate"] is False
    assert steps[:, 2].sum() == pytest.approx(0.01, abs=2e-4)


def test_done_shrinks_or_skips_the_edit():
    drv, steps = _loop(ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0), 6.5,
                       tip=_ramp((0.0, 0.0, 0.017)))
    r = _rec(drv)[0]
    assert r["verdict"] == "done" and r["frac_done"] == pytest.approx(0.85, abs=1e-3) and r["eat_candidate"] is True
    assert steps[:, 2].sum() == pytest.approx(0.5 * 0.02 * 0.15, abs=2e-4)
    drv2, steps2 = _loop(ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0), 6.5,
                         tip=_ramp((0.0, 0.0, 0.025)))
    assert _rec(drv2)[0]["factor"] == 0.0 and np.abs(steps2).sum() == 0.0
    assert [x["layer"] for x in drv2.log if x["type"] == "answer"][0] == "none"


def test_conflict_holds_and_rides_the_next_request_with_evidence():
    ast = ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0)
    drv, steps = _loop(ast, 3.5, tip=_ramp((0.0, 0.0, -0.02)))
    r = _rec(drv)[0]
    assert r["verdict"] == "conflict" and r["eat_candidate"] is True and r["cos"] == pytest.approx(-1.0)
    assert np.abs(steps).sum() == 0.0
    prev = ast.calls[1]["req"]["since_last_request"]["previous_request"]
    assert prev["reconcile"]["verdict"] == "conflict"
    assert prev["reconcile"]["vla_motion_m"] == [0.0, 0.0, -0.02]
    assert prev["edit"]["delta_position_m"] == [0.0, 0.0, 0.02]


def test_log_only_arm_keeps_the_pre_task19_path():
    """reconcile_apply False (the canon §92 P7 with / without arm): the verdict is logged, the command is not touched
    and the gate's stale drop stays."""
    drv, steps = _loop(ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0), 6.5,
                       tip=_ramp((0.0, 0.0, -0.02)), p=CoupleParams(reconcile_apply=False))
    r = _rec(drv)[0]
    assert (r["verdict"], r["action"]) == ("conflict", "log_only")
    assert steps[:, 2].sum() == pytest.approx(0.01, abs=2e-4)
    drv2, steps2 = _loop(ScriptedCoupleAstra([answer("edit", **EDIT_Z)], latency_s=16.0), 19.5,
                         p=CoupleParams(reconcile_apply=False))
    assert _rec(drv2)[0]["verdict"] == "valid" and np.abs(steps2).sum() == 0.0
    assert [x["gate"] for x in drv2.log if x["type"] == "answer"] == ["stale"]


def test_changed_by_segment_and_by_gripper_drops_the_command():
    drv, steps = _loop(ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0), 6.5,
                       phase=lambda now: "approach" if now < 2.0 else "descend")
    assert (_rec(drv)[0]["verdict"], _rec(drv)[0]["reason"]) == ("changed", "segment") and np.abs(steps).sum() == 0
    drv2, steps2 = _loop(ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0), 6.5,
                         t1=lambda now: {"holding_t": now >= 2.0})
    assert _rec(drv2)[0]["reason"] == "gripper" and np.abs(steps2).sum() == 0.0
    assert _rec(drv2)[0]["grip_from"] == {"holding_t": False} and _rec(drv2)[0]["grip_to"] == {"holding_t": True}


def test_stale_precedence_age_over_15s():
    ed = answer("edit", **EDIT_Z)
    drv, steps = _loop(ScriptedCoupleAstra([ed], latency_s=16.0), 19.5)  # still world: valid overrides the stale drop
    r = _rec(drv)[0]
    assert (r["verdict"], r["reason"]) == ("valid", "still") and r["age_s"] == pytest.approx(16.0)
    assert [x["gate"] for x in drv.log if x["type"] == "answer"] == ["ok"]
    assert steps[:, 2].sum() == pytest.approx(0.01, abs=2e-4)
    drv2, steps2 = _loop(ScriptedCoupleAstra([ed], latency_s=16.0), 18.0, tip=_ramp((0.03, 0.0, 0.0)))
    r2 = _rec(drv2)[0]
    assert (r2["verdict"], r2["reason"]) == ("changed", "stale") and np.abs(steps2).sum() == 0.0
    assert [x["gate"] for x in drv2.log if x["type"] == "answer"] == ["stale"]


def test_authority_zero_applies_nothing_but_logs_the_verdict():
    drv, steps = _loop(ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0), 6.5,
                       auth=lambda now: 0.0)
    r = _rec(drv)[0]
    assert r["verdict"] == "valid" and r["a"] == 0.0 and r["effective"] == 0.0
    assert np.abs(steps).sum() == 0.0


def test_vla_motion_excludes_the_coupling_bias():
    """The tip includes what the offset itself moved; the reconciliation compares the VLA's own motion."""
    ed = answer("edit", **EDIT_Z)
    applied = []

    def tip(now):
        return P0 + (np.sum(applied, axis=0)[:3] if applied else 0.0)
    q = MiniQueue()
    drv = CoupleDriver(CoupleParams(), ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0),
                       CostLedger(None, 0.0, PriceTable.free()), q.submit, "T")
    for i in range(700):
        now = round(i * 0.01, 6)
        for r in q.due(now):
            drv.on_delivery(r, now, {})
        out = drv.tick(TickView(now=now, dt=0.01, tcp_p=tip(now), phase="approach", stage="S1", near=False,
                                committed=SMALL_X, frames=FR, cams=CAMS, t1={}))
        applied.append(out.step6)
    rows = _rec(drv)
    assert [x["verdict"] for x in rows] == ["valid", "valid"]  # not 'done' from the bias's own 1 cm
    assert rows[1]["vla_motion_m"] == [0.0, 0.0, 0.0]


def test_request_context_keys_and_values():
    ast = ScriptedCoupleAstra([answer("edit", **EDIT_Z), answer("continue")], latency_s=3.0)
    chunk = np.array([0.0, 0.0, -0.01])
    _loop(ast, 3.5, tip=_ramp((0.0, 0.0, -0.02)), t1=lambda now: {"gripper_open": now < 1.0},
          step=lambda d, now: d.on_step(SMALL_X, "OK", now, chunk_vec=chunk), backend="fused")
    s0, s1 = ast.calls[0]["req"]["since_last_request"], ast.calls[1]["req"]["since_last_request"]
    assert s0["previous_request"] is None and s0["vla_chunks"] == 1 and s0["vla_gripper_events"] == []
    prev = s1["previous_request"]
    assert set(prev) == {"age_s", "t_state", "command", "segment", "edit", "reconcile"}
    assert prev["t_state"] == 0.0 and prev["command"] == "edit"
    assert set(prev["reconcile"]) == {"verdict", "reason", "vla_motion_m", "cos", "frac_done", "age_s", "action"}
    # the gripper closed at 1.0 s after the request's state (gripper_open True -> False): changed, edit dropped
    assert (prev["reconcile"]["verdict"], prev["reconcile"]["action"]) == ("changed", "dropped")
    assert s1["vla_tip_moved_m"] == [0.0, 0.0, -0.02]
    assert s1["vla_chunks"] == 10  # decision steps at 0.00, 0.33, ... 2.97 with an executed chunk
    assert s1["vla_gripper_events"] == [{"t": 1.0, "gripper": "closed"}]


def test_summary_counts_and_eat_candidates():
    script = [answer("edit", **EDIT_Z), answer("continue")]
    drv, _ = _loop(ScriptedCoupleAstra(script, latency_s=3.0), 9.5, tip=_ramp((0.0, 0.0, -0.02)))
    s = drv.summary()["reconcile"]
    assert s["counts"] == {"conflict": 1, "valid": 2} and s["eat_candidates"] == 1
    assert s["outcome_join"] == "episode+no"


# ------------------------------------------------------------------ predicted state (ruling R19, P113)
def _stop_tip(now):
    """Moves 6 cm in +y over 2.0-2.9 s, then stops (the E-ACC P113 case: short motion then a stop)."""
    return P0 + np.array([0.0, 0.06, 0.0]) * min(1.0, max(0.0, (now - 2.0) / 0.9))


def test_predicted_state_near_a_stop_stays_within_the_chunk_displacement():
    chunk = np.array([0.0, 0.0, -0.008])
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _loop(ast, 3.5, tip=_stop_tip, backend="fused",
          step=lambda d, now: d.on_step(SMALL_X, "OK", now, chunk_vec=chunk))
    req = ast.calls[1]["req"]  # sent at 3.0 s, 0.1 s after the stop
    pe = req["predicted_ee_at_arrival"]
    d = np.asarray(pe["pos_m"]) - np.asarray(req["tip_now_m"])
    assert np.linalg.norm(d) <= np.linalg.norm(chunk) + 1e-6 and pe["method"].startswith("chunk")
    ast2 = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _loop(ast2, 3.5, tip=_stop_tip, backend="fused", p=CoupleParams(predict_mode="extrapolate"),
          step=lambda d, now: d.on_step(SMALL_X, "OK", now, chunk_vec=chunk))
    req2 = ast2.calls[1]["req"]
    d2 = np.asarray(req2["predicted_ee_at_arrival"]["pos_m"]) - np.asarray(req2["tip_now_m"])
    assert np.linalg.norm(d2) > 0.05 and req2["predicted_ee_at_arrival"]["method"].startswith("extrapolate")


def test_predicted_state_sources_by_backend():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _loop(ast, 1.0, tip=_stop_tip, backend="fused")  # fused, no executing chunk: the tip itself
    r = ast.calls[0]["req"]
    assert r["predicted_ee_at_arrival"]["pos_m"] == r["tip_now_m"]
    ast2 = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _loop(ast2, 1.0, backend="modular")  # modular: the decision centre capped by the skill travel (1 cm)
    r2 = ast2.calls[0]["req"]
    assert r2["predicted_ee_at_arrival"]["pos_m"] == [1.01, 0.0, 0.0]


def test_predict_mode_is_validated():
    with pytest.raises(ValueError):
        CoupleParams(predict_mode="velocity")
    with pytest.raises(ValueError):
        CoupleParams(recon_done_frac=0.0)
    p = CoupleParams()
    assert (p.predict_mode, p.recon_done_frac, p.recon_still_m, p.reconcile_apply) == ("chunk", 0.8, 0.01, True)
