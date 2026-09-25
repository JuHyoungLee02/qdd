"""R7 cycle 12 D3: the (b) category of the finished step goes into the next decision request (M4 §4.2 :232
`next_jev_input.add_line(f"last_step: {s.outcome}")`, C4 "범주" :340, C5 "§4.2 전체" :341, C6 = C5 without overlap),
and NOT for C5' (:342 "C5에서 (b) 범주를 Jev 입력에서 뺌") nor the conditions without (b) (C0-C3). Canon §77."""
import pytest

from harvest.runtime.conditions import condition
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.m4 import M4Params
from harvest.runtime.models import MockFusedModel, MockSelector

from .fakeworld import FakeWorld

INJECT_TICK = 400  # 4.00 s: the step running then ends with DEVIATE


class Recording(MockSelector):
    def __init__(self, base):
        self.base, self.seen = base, []
        self.synthetic_latency = base.synthetic_latency
        self.model_id = base.model_id
        for k in ("synthetic_chunk_latency", "H", "chunk_dt"):
            if hasattr(base, k):
                setattr(self, k, getattr(base, k))

    def decide(self, ctx):
        self.seen.append((ctx["t_state"], ctx["req"]["state"]))
        return self.base.decide(ctx)

    def chunk(self, ctx, committed):
        return self.base.chunk(ctx, committed)


def _run(cond, backend="modular", ticks=700):
    m4, rt_over = condition(cond)
    base = MockFusedModel(latency_s=0.30) if backend == "fused" else MockSelector(latency_s=0.30)
    model = Recording(base)
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="none", condition=cond,
                        m4={**M4Params().__dict__, **m4}, **rt_over)
    rt = OursRuntime(cfg, model)
    rt.reset()
    w = FakeWorld()
    t_dev = None
    for i in range(ticks):
        if i == INJECT_TICK:
            if backend == "fused":  # fused (b)(1) = joint residual vs the chunk (core._joint_outcome)
                orig = rt._joint_outcome

                def once(orig=orig):
                    rt._joint_outcome = orig
                    return "DEVIATE", 0.2
                rt._joint_outcome = once
            else:
                rt.skill.pending_outcome = "DEVIATE"
        a, _ = rt.act(w.obs())
        w.step(a)
        if t_dev is None and any(s.get("prev_outcome") == "DEVIATE" for s in rt.slots_log):
            t_dev = next(s["t"] for s in rt.slots_log if s.get("prev_outcome") == "DEVIATE")
    rt.close()
    return rt, model.seen, t_dev


def _last_line(state):
    lines = state.split("\n")
    assert sum(ln.startswith("last_step:") for ln in lines) == 1, state
    assert lines[-1].startswith("last_step: "), state
    return lines[-1][len("last_step: "):]


@pytest.mark.parametrize("backend", ["modular", "fused"])
@pytest.mark.parametrize("cond", ["C4", "C5", "C6"])
def test_next_request_after_a_forced_deviate_carries_it(cond, backend):
    rt, seen, t_dev = _run(cond, backend)
    assert t_dev is not None
    vals = [(t, _last_line(s)) for t, s in seen]
    assert vals[0][1] == "none"  # no step has finished at the first call
    # requests built after the boundary tick that checked the step (a call sent at that same tick is built before
    # the check, core.act order: calls -> deliveries -> boundary); DEVIATE pulls an early call to the next tick
    after = [v for t, v in vals if t_dev + 1e-9 < t < t_dev + 0.33 - 1e-6]
    assert after and all(v == "DEVIATE" for v in after), (t_dev, after)
    assert {v for _, v in vals} <= {"none", "OK", "LAG", "DEVIATE", "CONTRADICT"}
    assert rt.cfg.b_to_model is True


@pytest.mark.parametrize("cond", ["C5'", "C0", "C1", "C2", "C3"])
def test_no_outcome_in_the_request_for_c5prime_and_conditions_without_b(cond):
    rt, seen, t_dev = _run(cond)
    assert t_dev is not None  # the (b) check itself still runs (C5': code replanning only)
    assert seen and {_last_line(s) for _, s in seen} == {"none"}


def test_c5prime_is_c5_with_the_b_line_off_only():
    m5, r5 = condition("C5")
    mp, rp = condition("C5'")
    assert mp == m5 and rp == {**r5, "b_to_model": False}
    rt, _, t_dev = _run("C5'")
    assert rt.ledger.epoch >= 1  # (b) epoch invalidation kept (M4 :342 "코드 재계획만")
