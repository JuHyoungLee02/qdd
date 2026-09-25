"""R7 cycle 13 N1: a decision request sent at a decision-step boundary tick carries the category of the step that just
finished at that tick -- the same pairing as the training items (snapshot k carries the step that ended at k,
deccall_snap.annotate_last_step, canon §77 (iv)). M4 §4.2 :232 `next_jev_input.add_line(f"last_step: {s.outcome}")`
in on_step_executed: the Jev input built after the step's check is the "next" one. Before this fix the call of the
boundary tick was built before the boundary check (core.act: calls -> deliveries -> boundary) and carried the step
before (LAG at the 4.29 s boundary first appeared on the 4.62 s call). Canon §79."""
import pytest

from harvest.runtime.conditions import condition
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.m4 import M4Params
from harvest.runtime.models import MockFusedModel, MockSelector

from .fakeworld import FakeWorld
from .test_r7c12_b_feedback import Recording, _last_line


def _run(cond, outcome, backend="modular", inject=400, ticks=700):
    m4, rt_over = condition(cond)
    base = MockFusedModel(latency_s=0.30) if backend == "fused" else MockSelector(latency_s=0.30)
    model = Recording(base)
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="none", condition=cond,
                        m4={**M4Params().__dict__, **m4}, **rt_over)
    rt = OursRuntime(cfg, model)
    rt.reset()
    w = FakeWorld()
    for i in range(ticks):
        if i == inject:
            if backend == "fused":
                orig = rt._joint_outcome

                def once(orig=orig):
                    rt._joint_outcome = orig
                    return outcome, 0.1
                rt._joint_outcome = once
            else:
                rt.skill.pending_outcome = outcome
        a, _ = rt.act(w.obs())
        w.step(a)
    rt.close()
    return rt, model.seen


@pytest.mark.parametrize("backend", ["modular", "fused"])
@pytest.mark.parametrize("outcome", ["LAG", "DEVIATE"])
@pytest.mark.parametrize("cond", ["C4", "C5", "C6"])
def test_boundary_tick_request_carries_the_just_finished_step(cond, outcome, backend):
    rt, seen = _run(cond, outcome, backend)
    bounds = {round(s["t"], 4): s["prev_outcome"] for s in rt.slots_log if "prev_outcome" in s}
    at_b = [(round(t, 4), _last_line(s)) for t, s in seen if round(t, 4) in bounds]
    assert len(at_b) >= 3, at_b  # periodic calls fall on boundary ticks (grid-aligned T_c)
    for t, v in at_b:
        assert v == bounds[t], (t, v, bounds[t])
    t_inj = next(t for t, o in sorted(bounds.items()) if o == outcome)
    assert (t_inj, outcome) in at_b or not any(t == t_inj for t, _ in at_b)
    # every request carries the last finished step's category (none only before the first boundary check)
    for t, s in seen:
        done = [o for tb, o in sorted(bounds.items()) if tb <= round(t, 4) + 1e-9]
        assert _last_line(s) == (done[-1] if done else "none"), (t, _last_line(s))


def test_the_lag_boundary_call_carries_lag():
    """The reviewer's case (r7_cycle13 N1): LAG at the 4.29 s boundary; the 4.29 s call now carries LAG."""
    rt, seen = _run("C5", "LAG")
    t_lag = next(round(s["t"], 4) for s in rt.slots_log if s.get("prev_outcome") == "LAG")
    same = [_last_line(s) for t, s in seen if round(t, 4) == t_lag]
    assert same == ["LAG"], (t_lag, same)
