"""Runtime wiring of the agreed Astra segment plan into the VLA segment line (plan 2026-09-26 Task 18, brief §3): the
fused runtime's decision state carries the line mapped from the agreed plan -- now via intent.PLAN_TO_LINE, do / next
from intent.SEGMENT_PLAN of the mapped segment (the line vocabulary the VLA was trained on), never Astra's raw
do / next -- after two agreeing answers, unknown before and with the coupling off."""
import numpy as np

from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockFusedModel
from harvest.serialize import SEGMENT_UNKNOWN

from .fakeworld import FakeWorld

FRAME = np.full((12, 16, 3), 60, np.uint8)
LIFT = {"now": "lift", "do": "none", "next": "carry"}  # raw: lift -> line carry, SEGMENT_PLAN carry = (open, retreat)


def test_fused_decision_state_carries_the_mapped_line_after_two_agreeing_answers():
    cfg = RuntimeConfig(backend="fused", clock="simlat", astra_mode="mock", couple="serial",
                        couple_params={"request_mode": "F0"})
    rt = OursRuntime(cfg, MockFusedModel(latency_s=0.3),
                     astra=ScriptedCoupleAstra([answer("continue", segment=LIFT)], latency_s=3.0))
    rt.reset()
    w = FakeWorld()
    lines = []
    for i in range(700):
        o = w.obs()
        if i % 10 == 0:
            o["images"] = {c: FRAME for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
        a, _ = rt.act(o)
        w.step(a)
        lines.append((rt.t_last, rt.segment_intent))
    before = [s for t, s in lines if t < 2.9]
    assert before and set(before) == {SEGMENT_UNKNOWN}  # no answer yet
    line = "segment: now=carry do=open next=retreat"
    assert lines[-1][1] == line and rt.driver.layer.plan == LIFT
    first = min(t for t, s in lines if s == line)
    assert 5.9 < first < 6.2  # the second agreeing answer (sends 0 / 3 s, latency 3 s)
    ctx = rt._decision_ctx(rt.t_last, *rt._m1_last[:4], w.obs())
    assert ctx["segment"] == line and ctx["ctx_text"].split("\n")[-2] == line
    assert ctx["req"]["state"].split("\n")[-3] == line
    assert rt.driver.backend == "fused"  # Task 18 fix I1: the runtime tells the driver its backend
    rt.close()


def test_coupling_off_keeps_the_line_unknown():
    rt = OursRuntime(RuntimeConfig(backend="fused", clock="simlat"), MockFusedModel(latency_s=0.3))
    rt.reset()
    w = FakeWorld()
    for _ in range(300):
        a, _ = rt.act(w.obs())
        w.step(a)
    assert rt.segment_intent == SEGMENT_UNKNOWN
    rt.close()
