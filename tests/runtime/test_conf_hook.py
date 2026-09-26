"""E-CONF logging hook wired into OursRuntime._deliver (canon §95, plan Task 22): every successful decision call
(`rt.calls`, which `ir_policy.on_trial_end` serialises byte for byte into the per-trial sidecar's "call" rows,
canon §42) carries a conf-base@v1 block, and the hook changes NO robot behaviour (no gate, §95 (a)/(b) OFF)."""
import numpy as np

from harvest.runtime import core as core_mod
from harvest.runtime.astra_hb import MockAstra
from harvest.runtime.confidence import VER
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockFusedModel, MockSelector

from .fakeworld import FakeWorld


def _run(backend, model, seconds, astra=None):
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="mock" if astra else "none")
    rt = OursRuntime(cfg, model, astra=astra)
    rt.reset()
    w = FakeWorld()
    actions = []
    for _ in range(int(seconds * 100)):
        a, _ = rt.act(w.obs())
        w.step(a)
        actions.append(np.asarray(a, float).copy())
    rt.close()
    return rt, np.stack(actions)


def _check_conf_rows(calls, questions):
    assert calls
    for c in calls:
        assert c["error"] is None
        conf = c["conf"]
        assert conf["ver"] == VER
        assert set(conf["per_q"]) == set(questions)
        assert conf["argmin_q"] in questions
        for q, pq in conf["per_q"].items():
            assert {"top1", "top2", "margin"} <= set(pq)


def test_conf_attached_to_every_modular_call():
    rt, _ = _run("modular", MockSelector(latency_s=0.30), 3.0, astra=MockAstra(3.0))
    from harvest.runtime.models import DECISION_QUESTIONS
    _check_conf_rows(rt.calls, DECISION_QUESTIONS)
    # MockSelector (models.py:120): p_chosen=1.0 / p_second=0.0 on every question -> every margin is the +inf case,
    # tied -> the argmin is the first question of DECISION_QUESTIONS, and the joint is finite (-ln(1.0) * 5 = 0.0)
    c0 = rt.calls[0]["conf"]
    assert c0["argmin_q"] == DECISION_QUESTIONS[0]
    assert c0["min_margin"] is None and all(pq["margin_inf"] == 1 for pq in c0["per_q"].values())
    assert c0["joint"] == 0.0 and "joint_inf" not in c0


def test_conf_attached_to_every_fused_call():
    rt, _ = _run("fused", MockFusedModel(latency_s=0.30), 3.0)
    from harvest.runtime.models import FUSED_QUESTIONS
    _check_conf_rows(rt.calls, FUSED_QUESTIONS)


def test_actions_are_byte_identical_with_and_without_the_hook(monkeypatch):
    """Disable the hook at its one call site (core._deliver) and compare against the normal run: identical action
    stream, identical decision/vote/outcome bookkeeping, only the "conf" key differs on the call rows."""
    rt_on, a_on = _run("fused", MockFusedModel(latency_s=0.30), 3.0)
    monkeypatch.setattr(core_mod, "conf_from_answers", lambda answers: None)
    rt_off, a_off = _run("fused", MockFusedModel(latency_s=0.30), 3.0)
    assert a_on.tobytes() == a_off.tobytes()
    assert len(rt_on.calls) == len(rt_off.calls)
    drop = {"conf", "call_id"}  # call_id is a fresh uuid4 per call (models.py), not part of "behaviour"
    for con, coff in zip(rt_on.calls, rt_off.calls):
        assert "conf" not in coff
        without_conf = {k: v for k, v in con.items() if k not in drop}
        assert without_conf == {k: v for k, v in coff.items() if k not in drop}
    assert [s["decisions"] for s in rt_on.slots_log] == [s["decisions"] for s in rt_off.slots_log]
    assert [s.get("outcome") for s in rt_on.slots_log] == [s.get("outcome") for s in rt_off.slots_log]
