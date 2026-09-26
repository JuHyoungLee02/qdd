"""Runtime side of the gripper decision question (canon §87, plan 2026-09-26 Task 12): the fused backend asks and
commits it (the modular stack does not); the committed decision conditions the chunk request and reaches the coupling
request's vla_now; it is an INTENT only -- a gripper close in the chunk still needs the two-layer gate's T1 premise
(canon §84 / §86, plan R1)."""
import numpy as np

from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import DECISION_QUESTIONS, FUSED_QUESTIONS, MockFusedModel, MockSelector, ModelResult

from .fakeworld import HM, TZ, FakeWorld

FRAME = np.full((12, 16, 3), 60, np.uint8)


class _CloseIntentFused(MockFusedModel):
    """Always decides gripper = close; its chunk closes the gripper exactly when the committed gripper decision is
    close (the conditioning a trained expert would follow, E-SR0 phase_id 0.95)."""

    def decide(self, ctx):
        r = super().decide(ctx)
        for a in r.answers.values():
            if ctx["shown"][a["qid"]][0] == "gripper":
                a.update(choice="close", probs={"close": 1.0})
        return r

    def chunk(self, ctx, committed):
        r = super().chunk(ctx, committed)
        c = r.chunk.copy()
        if committed.get("gripper") == "close":
            c[:, 7] = 0.0
        return ModelResult({}, r.latency_s, call_id=r.call_id, chunk=c, chunk_dt=r.chunk_dt, meta=r.meta)


def _run(world, seconds, model, backend="fused", couple="serial"):
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="mock", couple=couple,
                        couple_params={"request_mode": "F0"})
    rt = OursRuntime(cfg, model, astra=ScriptedCoupleAstra([answer("continue")], latency_s=3.0))
    rt.reset()
    widths = []
    for i in range(int(seconds * 100)):
        o = world.obs()
        if i % 10 == 0:
            o["images"] = {c: FRAME for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
        a, _ = rt.act(o)
        world.step(a)
        widths.append(world.width)
    return rt, widths


def test_fused_asks_and_commits_the_gripper_question_modular_does_not():
    rt, _ = _run(FakeWorld(), 2.0, MockFusedModel(latency_s=0.3), couple="off")
    assert rt.ledger.questions == FUSED_QUESTIONS
    assert any("gripper" in c["answers"] for c in rt.calls)
    assert rt.skill.dec.get("gripper") == "keep"  # the mock's rule label for the approach phase
    assert any(c["dec"].get("gripper") == "keep" for c in rt.chunk_log)  # the chunk request is conditioned on it
    rt.close()
    rt2, _ = _run(FakeWorld(), 2.0, MockSelector(latency_s=0.3), backend="modular", couple="off")
    assert all(set(c["answers"]) <= set(DECISION_QUESTIONS) for c in rt2.calls) and rt2.calls
    assert "gripper" not in rt2.skill.dec and rt2.ledger.questions == DECISION_QUESTIONS
    rt2.close()


def test_committed_close_intent_without_the_t1_premise_does_not_close():
    w = FakeWorld()  # the tip starts 7.8 cm from the mug: gripper open but NOT near -> no T1 close premise
    rt, widths = _run(w, 3.0, _CloseIntentFused(latency_s=0.3))
    assert rt.skill.dec.get("gripper") == "close"
    assert rt.chunk_stats["played"] > 0 and any(c["dec"].get("gripper") == "close" for c in rt.chunk_log)
    assert min(widths) == 0.107  # the chunk asked to close; the gate held the width every tick
    assert rt.driver.summary()["irrev"].get("deny:no_evidence", 0) >= 1
    req = rt.driver.request(_view(rt, w), 99, [], [])
    assert req["vla_now"]["committed"]["gripper"] == "close"  # the coupling request carries the intent
    rt.close()


def test_committed_close_intent_with_the_t1_premise_closes():
    w = FakeWorld()
    w.tcp = np.array([0.40, -0.20, TZ + HM + 0.02])  # above the mug centre, inside the 5 cm near zone
    w.a = np.r_[w.tcp, 0, 0, 0, 0, w.width]
    rt, widths = _run(w, 3.0, _CloseIntentFused(latency_s=0.3))
    assert min(widths) < 0.107 and rt.driver.summary()["irrev"].get("allow:t1_astra_stale", 0) >= 1
    rt.close()


def test_segment_intent_line_is_unknown_until_set_and_reaches_request_and_context():
    from harvest.serialize import MOTION_UNKNOWN, SEGMENT_UNKNOWN
    rt = OursRuntime(RuntimeConfig(backend="fused", clock="simlat"), MockFusedModel(latency_s=0.3))
    rt.reset()
    w = FakeWorld()
    for _ in range(40):
        a, _ = rt.act(w.obs())
        w.step(a)
    ctx = rt._decision_ctx(rt.t_last, *rt._m1_last[:4], w.obs())
    assert ctx["req"]["state"].split("\n")[-3:-1] == [SEGMENT_UNKNOWN, MOTION_UNKNOWN]  # no plan, no bins
    assert ctx["ctx_text"].split("\n")[-2:] == [SEGMENT_UNKNOWN, MOTION_UNKNOWN]
    assert ctx["privileged_s1"].split("\n")[-3] == SEGMENT_UNKNOWN  # never the skill's own phase
    plan = "segment: now=approach do=close next=carry"
    rt.segment_intent = plan  # what the coupling will set from Astra's agreed plan (later task)
    ctx = rt._decision_ctx(rt.t_last, *rt._m1_last[:4], w.obs())
    assert ctx["req"]["state"].split("\n")[-3] == plan and ctx["ctx_text"].split("\n")[-2] == plan
    rt.reset()
    assert rt.segment_intent == SEGMENT_UNKNOWN
    rt.close()


def test_offline_fused_context_helper_is_the_runtime_context():
    """Fix round 1 item 4: the fused canary / bench build ctx_text with models.fused_ctx_text -- byte-identical to the
    runtime's context (IMG state + segment line + motion line)."""
    from harvest.runtime.models import fused_ctx_text
    from harvest.serialize import MOTION_UNKNOWN, SEGMENT_UNKNOWN
    rt = OursRuntime(RuntimeConfig(backend="fused", clock="simlat"), MockFusedModel(latency_s=0.3))
    rt.reset()
    w = FakeWorld()
    for _ in range(40):
        a, _ = rt.act(w.obs())
        w.step(a)
    ctx = rt._decision_ctx(rt.t_last, *rt._m1_last[:4], w.obs())
    raw, present, pred, support = rt._m1_last[:4]
    s0 = rt._s0(rt.t_last, pred, present, support)
    assert ctx["ctx_text"] == fused_ctx_text(s0)  # no plan, no bins: unknown segment + motion
    assert ctx["ctx_text"].split("\n")[-2:] == [SEGMENT_UNKNOWN, MOTION_UNKNOWN]
    plan = "segment: now=carry do=open next=retreat"
    rt.segment_intent = plan
    ctx = rt._decision_ctx(rt.t_last, *rt._m1_last[:4], w.obs())
    assert ctx["ctx_text"] == fused_ctx_text(s0, segment=plan, motion=MOTION_UNKNOWN)
    rt.close()


def _view(rt, w):
    from harvest.couple.driver import TickView
    return TickView(now=rt.t_last, dt=rt.dt, tcp_p=w.tcp.copy(), phase=rt.skill.phase, stage=rt.skill.stage,
                    near=rt.near_now, committed={q: c for q, c in rt.skill.dec.items() if c is not None},
                    frames={}, t1=rt._t1(), motion=rt.motion.line())
