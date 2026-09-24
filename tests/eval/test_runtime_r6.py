"""R6 runtime additions: M4 comparison conditions C0-C6 (M4 §5 minimal set) and the J5 calibration gate."""
import json

import numpy as np
import pytest

from harvest.runtime.conditions import CONDITIONS, condition
from harvest.runtime.m4 import CommitLedger, M4Params, Vote


def _v(ds, choice, t_state, call="c", epoch=0, q="dir_xy"):
    return Vote(ds=ds, question=q, choice=choice, p_chosen=0.9, call_id=call, t_send=t_state, t_recv=t_state + 0.3,
                t_state=t_state, premise_epoch=epoch)


def test_newest_agreement_takes_the_vote_with_the_newest_state_and_never_commits():
    L = CommitLedger(M4Params(agree="newest"), questions=("dir_xy",))
    assert L.on_vote(_v(5, "plus_x", 0.5), now=0.8) == "newest"
    assert L.on_vote(_v(5, "minus_x", 0.83), now=1.1) == "newest"
    assert L.decision("dir_xy", 5) == ("minus_x", "TENTATIVE")
    assert L.on_vote(_v(5, "plus_y", 0.2), now=1.2) == "older"  # older request time: ignored
    assert L.decision("dir_xy", 5)[0] == "minus_x"
    assert L.try_commit_prefix("dir_xy", now=1.2) == []


def test_feedback_off_ignores_deviate():
    L = CommitLedger(M4Params(feedback_b=False), questions=("dir_xy",))
    L.on_vote(_v(5, "plus_x", 0.5), now=0.8)
    sig = L.on_step_executed(1, "DEVIATE", now=0.9)
    assert sig == {"epoch": 0, "early_call": False, "hold": False, "reopened": 0}
    assert L.epoch == 0 and L.last_bad_t is None


def test_max_inflight_caps_n_max():
    assert CommitLedger(M4Params(max_inflight=1, d_p95_init=0.9)).n_max() == 1
    assert CommitLedger(M4Params(d_p95_init=0.9)).n_max() == 4


def test_condition_table():
    assert set(CONDITIONS) == {"C0", "C1", "C2", "C3", "C4", "C5", "C6"}
    m4, rt = condition("C5")
    assert m4 == {} and rt == {}
    m4, rt = condition("C0")
    assert m4["max_inflight"] == 1 and rt["stop_wait"] is True
    assert condition("C2")[0] == {"agree": "newest", "feedback_b": False}
    assert condition("C6")[0] == {"max_inflight": 1}
    with pytest.raises(ValueError):
        condition("C5-A3")


# ------------------------------------------------------------------------------------------ fake-world runs
def _run(cond, seconds=40.0):
    from harvest.runtime.core import OursRuntime, RuntimeConfig
    from harvest.runtime.models import MockSelector
    from tests_fakeworld import FakeWorld
    m4, rt_over = condition(cond)
    from dataclasses import asdict
    cfg = RuntimeConfig(backend="modular", clock="simlat", astra_mode="none", condition=cond,
                        m4={**asdict(M4Params()), **m4}, **rt_over)
    rt = OursRuntime(cfg, MockSelector(latency_s=0.30))
    rt.reset()
    w = FakeWorld()
    moved_in_flight = []
    for _ in range(int(seconds * 100)):
        before = w.tcp.copy()
        a, meta = rt.act(w.obs())
        infl = sum(1 for it in rt.q._items if it["meta"]["kind"] == "dec")
        w.step(a)
        moved_in_flight.append((infl, float(np.linalg.norm(w.tcp - before))))
    rt.close()
    return rt, w, moved_in_flight


@pytest.fixture(autouse=True)
def _fakeworld_path(monkeypatch):
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime"))
    import fakeworld
    sys.modules["tests_fakeworld"] = fakeworld
    yield


@pytest.mark.parametrize("cond", ["C1", "C2", "C3", "C4", "C5", "C6"])
def test_every_condition_completes_the_fake_task(cond):
    rt, w, _ = _run(cond)
    assert np.all(np.abs(w.mug[:2] - w.tray[:2]) < [0.09, 0.07]) and not w.held, cond
    s = rt.summary()
    assert s["call_errors"] == 0 and s["condition"] == cond


def test_c0_holds_the_arm_while_a_call_is_in_flight():
    rt, w, mv = _run("C0", seconds=6.0)
    moving_in_flight = [d for infl, d in mv if infl > 0 and d > 1e-6]
    assert len(moving_in_flight) == 0
    assert rt.summary()["calls_delivered"] > 5


# ------------------------------------------------------------------------------------------ embodiment seed guard
def test_aiworker_layout_seed_guard():
    from harvest.runtime.aiworker import check_layout_seed
    assert check_layout_seed(3, env={}) == 3
    for s in (500, 1000, 1300, 2000, 31):
        with pytest.raises(ValueError):
            check_layout_seed(s, env={})
    assert check_layout_seed(1000, env={"HARVEST_ALLOW_SPLIT": "test"}) == 1000
    with pytest.raises(ValueError):
        check_layout_seed(1000, env={"HARVEST_ALLOW_SPLIT": "cal"})
    with pytest.raises(ValueError):
        check_layout_seed(2000, env={"HARVEST_ALLOW_SPLIT": "pool"})  # pool is not a closed-loop split


# ------------------------------------------------------------------------------------------ J5 gate
def _cal_file(tmp_path, qhat):
    d = {"format": "r6-calib-v1", "model": {"fingerprint": None}, "question_ids": {},
         "questions": {"dir_z": {"T_used": 1.0, "j5": {"0.1": {"qhat": qhat}}, "j5_ok": {"0.1": True}}}}
    p = tmp_path / "c.json"
    p.write_text(json.dumps(d))
    return str(p)


def test_j5_gate_holds_non_singleton_sets_and_escalates_after_two(tmp_path):
    from harvest.runtime.core import OursRuntime, RuntimeConfig
    from harvest.runtime.models import MockSelector, ModelResult
    cfg = RuntimeConfig(calibration=_cal_file(tmp_path, 0.6), j5_alpha=0.1, astra_mode="none")
    rt = OursRuntime(cfg, MockSelector())
    rt.reset()
    two = ModelResult({"dir_z": {"choice": "down", "p_chosen": 0.55, "p_second": 0.45,
                                 "probs": {"down": 0.55, "up": 0.45}}}, 0.3)
    one = ModelResult({"dir_z": {"choice": "down", "p_chosen": 0.9, "p_second": 0.1,
                                 "probs": {"down": 0.9, "up": 0.1}}}, 0.3)
    assert rt._j5(two, now=1.0) == {"dir_z": "hold"}
    assert rt._j5(two, now=1.33) == {"dir_z": "escalate"}
    assert rt._j5(one, now=1.66) == {}
    assert rt.j5_stats == {"held": 2, "escalated": 1, "passed": 1}
    rt.close()


def test_calibration_refused_for_another_model(tmp_path):
    from harvest.runtime.core import OursRuntime, RuntimeConfig
    from harvest.runtime.models import MockSelector
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"format": "r6-calib-v1", "model": {"fingerprint": "AAA"}, "question_ids": {},
                             "questions": {}}))
    with pytest.raises(ValueError, match="fingerprint"):
        OursRuntime(RuntimeConfig(calibration=str(p), j5_alpha=0.1, model_fingerprint="BBB"), MockSelector())
