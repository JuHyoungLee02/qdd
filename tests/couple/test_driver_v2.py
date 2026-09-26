"""CoupleDriver under astra-couple@v2 (plan 2026-09-26 Task 18): the request / prompt / id, the committed arrow =
the executed chunk motion (modular: the decision centre capped by what the skill travels in 0.5 s), the
since_last_request context (canon §91), the agreed segment plan and its runtime line (PLAN_TO_LINE + SEGMENT_PLAN),
the a = 0 freeze at delivery, valid_until segment_end, the AxisGuide flag and v1 still selectable."""
import json

import numpy as np
import pytest

from harvest.couple import prompt as CP
from harvest.couple import prompt_v2 as V2
from harvest.couple.cost import CostLedger, PriceTable
from harvest.couple.driver import CoupleDriver, TickView
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.couple.params import CoupleParams
from harvest.serialize import SEGMENT_UNKNOWN

from .test_driver import CAMS, FR, MiniQueue

SMALL_X = {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"}
D = {"now": "descend", "do": "none", "next": "grasp"}
G = {"now": "grasp", "do": "close", "next": "lift"}


def _loop(astra, seconds, p=None, phase=lambda now: "approach", auth=lambda now: None, step=None, tip=None,
          backend=None):
    """step: callable(drv, now) run at every 0.33 s boundary (on_step calls); tip: callable(now) -> tcp."""
    p = p or CoupleParams()
    q = MiniQueue()
    drv = CoupleDriver(p, astra, CostLedger(None, 0.0, PriceTable.free()), q.submit, "Put the red mug on the tray.",
                       backend=backend)
    outs = []
    for i in range(int(round(seconds * 100))):
        now = round(i * 0.01, 6)
        for r in q.due(now):
            drv.on_delivery(r, now, {})
        if step is not None and i % 33 == 0:
            step(drv, now)
        tcp = np.array([1.0, 0.0, 0.0]) if tip is None else tip(now)
        outs.append(drv.tick(TickView(now=now, dt=0.01, tcp_p=tcp, phase=phase(now), stage="S1", near=False,
                                      committed=SMALL_X, frames=FR, cams=CAMS, t1={}, authority=auth(now))))
    return drv


def test_v2_request_prompt_and_id():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    drv = _loop(ast, 7.0)
    r0, r1 = ast.calls[0]["req"], ast.calls[1]["req"]
    assert r0["schema"] == "astra-couple@v2" and r0["since_last_request"]["previous_request"] is None
    assert r0["since_last_request"]["vla_phases"] == ["approach"]
    prev = r1["since_last_request"]["previous_request"]
    assert prev == {"age_s": 3.0, "command": "continue", "segment": {"now": "approach", "do": "none",
                                                                     "next": "descend"}}
    assert r1["since_last_request"]["vla_tip_moved_m"] == [0.0, 0.0, 0.0]
    ans = [r for r in drv.log if r["type"] == "answer"]
    assert {r["prompt_id"] for r in ans} == {V2.PROMPT_ID["F0"]} == {"83fa03a5de19"}
    assert drv.summary()["prompt_id"] == "83fa03a5de19" and drv.summary()["schema"] == "astra-couple@v2"
    assert ans[0]["segment"] == {"now": "approach", "do": "none", "next": "descend"}


def test_v2_prompt_text_is_the_ported_builder_with_the_drawn_legend():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    drv = CoupleDriver(CoupleParams(), ast, CostLedger(None, 0.0, PriceTable.free()), MiniQueue().submit, "T")
    inp = drv._build({"request_no": 1, "events": []}, {"cam_head": b"\xff\xd8x"},
                     {"head": {"ring", "axes", "next"}, "wrist": None, "axisguide": []})
    assert inp == V2.build({"request_no": 1, "events": []}, {"cam_head": b"\xff\xd8x"}, list(CoupleParams().cameras),
                           "T", horizon_s=9.3, drawn={"head": {"ring", "axes", "next"}, "wrist": None,
                                                      "axisguide": []})
    text = inp[0]["content"][0]["text"]
    assert V2.FRAME in text and V2.DEFS in text and "THICK SOLID pale-green arrow" in text
    assert "trace" not in text.split("Overlay on cam_head")[1].split("\n")[0]  # only the elements drawn


def test_committed_arrow_is_the_executed_chunk_vector_on_the_fused_path():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    chunk = np.array([0.0, 0.038, 0.0])
    _loop(ast, 3.5, step=lambda drv, now: drv.on_step(SMALL_X, "OK", now, chunk_vec=chunk))
    assert ast.calls[1]["req"]["vla_now"]["next_motion_m"] == [0.0, 0.038, 0.0]
    assert ast.calls[1]["req"]["vla_now"]["arrow_src"] == "chunk"


def test_modular_arrow_is_the_decision_capped_by_the_skill_travel():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _loop(ast, 3.5, step=lambda drv, now: drv.on_step(SMALL_X, "OK", now))
    assert ast.calls[0]["req"]["vla_now"]["next_motion_m"] == [0.01, 0.0, 0.0]  # small centre 1 cm < 0.2 m/s x 0.5 s
    ast2 = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _loop(ast2, 1.0, phase=lambda now: "close")  # the skill does not move in close: no arrow
    assert ast2.calls[0]["req"]["vla_now"]["next_motion_m"] is None
    ast3 = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _loop(ast3, 1.0, p=CoupleParams(prompt_version="v1"))  # v1: the decision-token centre, as before
    assert ast3.calls[0]["req"]["vla_now"]["next_motion_m"] == [0.01, 0.0, 0.0]
    assert "arrow_src" not in ast3.calls[0]["req"]["vla_now"]


def test_agreed_plan_and_its_runtime_line():
    ast = ScriptedCoupleAstra([answer("continue", segment=D)], latency_s=3.0)
    drv = _loop(ast, 3.5)
    assert drv.layer.plan is None and drv.segment_intent() == SEGMENT_UNKNOWN
    drv = _loop(ScriptedCoupleAstra([answer("continue", segment=D)], latency_s=3.0), 6.5)
    assert drv.layer.plan == D
    # descend -> line approach; do / next from SEGMENT_PLAN["approach"], NOT Astra's raw none / grasp
    assert drv.segment_intent() == "segment: now=approach do=close next=carry"
    assert [r["plan"] for r in drv.log if r["type"] == "answer"] == ["plan_candidate", "plan_agreed"]
    assert drv.summary()["segment_plan"] == D


def test_a0_at_delivery_freezes_the_agreed_do():
    script = [answer("continue", segment=D), answer("continue", segment=D), answer("continue", segment=G)]
    drv = _loop(ScriptedCoupleAstra(script, latency_s=3.0), 12.5, auth=lambda now: 1.0 if now < 7.0 else 0.0)
    plans = [r["plan"] for r in drv.log if r["type"] == "answer"]
    assert plans == ["plan_candidate", "plan_agreed", "plan_candidate", "plan_frozen"]
    assert drv.layer.plan == D


def test_valid_until_segment_end_drops_the_correction_when_the_phase_changes():
    ed = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.02), valid_until="segment_end")
    drv = _loop(ScriptedCoupleAstra([ed, answer("continue")], latency_s=3.0), 5.0,
                phase=lambda now: "approach" if now < 3.5 else "descend", auth=lambda now: 1.0)
    rows = [r for r in drv.log if r.get("type") == "segment_end"]
    assert len(rows) == 1 and rows[0]["t"] == pytest.approx(3.5) and not drv.offset.active
    ed2 = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.02))  # next_answer: kept
    drv2 = _loop(ScriptedCoupleAstra([ed2, answer("continue")], latency_s=3.0), 5.0,
                 phase=lambda now: "approach" if now < 3.5 else "descend", auth=lambda now: 1.0)
    assert not [r for r in drv2.log if r.get("type") == "segment_end"]


def test_axis_guide_and_extra_instruction_flags():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    p = CoupleParams(axis_guide=True, extra_instruction="Check the target first.")
    drv = _loop(ast, 3.5, p=p)
    pid = [r["prompt_id"] for r in drv.log if r["type"] == "answer"][0]
    assert pid == V2.variant_id(axisguide=True, extra="Check the target first.")
    body = json.loads([b for ext, b in drv.blobs.values() if ext == "json"][0])
    seen = body["payload"]["input"][0]["content"][0]["text"]
    assert body["payload"]["prompt_id"] == pid
    assert "Axis guide on cam_head" in seen and "Check the target first.\n" + CP.MODE_RULES["F0"] in seen


def test_v1_is_selectable_and_logs_the_v1_id():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    drv = _loop(ast, 3.5, p=CoupleParams(prompt_version="v1"))
    r = ast.calls[0]["req"]
    assert r["schema"] == "astra-couple@v1" and "since_last_request" not in r
    assert {x["prompt_id"] for x in drv.log if x["type"] == "answer"} == {CP.PROMPT_ID["F0"]}
    assert drv.segment_intent() == SEGMENT_UNKNOWN


def _texts(drv):
    return [json.loads(b)["payload"]["input"][0]["content"][0]["text"] for ext, b in drv.blobs.values()
            if ext == "json"]


def test_fix_i1_fused_without_an_executing_chunk_draws_no_arrow():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    drv = _loop(ast, 3.5, backend="fused", step=lambda d, now: d.on_step(SMALL_X, "OK", now, chunk_vec=None))
    va = ast.calls[0]["req"]["vla_now"]
    assert va["next_motion_m"] is None and va["arrow_src"] == "none"
    t = _texts(drv)[0]
    assert "THICK SOLID" not in t and "Overlay on cam_head" in t and "; cyan solid arrow" not in t
    assert drv.prompt_id() == "83fa03a5de19"  # the adopted bytes, only the drawn legend differs
    ast2 = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    drv2 = _loop(ast2, 3.5, backend="fused",
                 step=lambda d, now: d.on_step(SMALL_X, "OK", now, chunk_vec=np.array([0.0, 0.03, 0.0])))
    assert ast2.calls[0]["req"]["vla_now"]["arrow_src"] == "chunk" and "THICK SOLID" in _texts(drv2)[0]
    ast3 = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _loop(ast3, 1.0, backend="modular")
    assert ast3.calls[0]["req"]["vla_now"]["next_motion_m"] == [0.01, 0.0, 0.0]  # modular keeps the capped arrow


def test_fix_m1_segment_end_clears_the_layer_edit():
    ed = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.02), valid_until="segment_end")
    drv = _loop(ScriptedCoupleAstra([ed, answer("continue")], latency_s=3.0), 3.6,
                phase=lambda now: "approach" if now < 3.5 else "descend", auth=lambda now: 1.0)
    row = [r for r in drv.log if r.get("type") == "segment_end"][0]
    assert row["layer_cleared"] is True and drv.layer.pending is None and drv.layer.confirmed is None
    assert drv.layer.counts["edit_cleared"] == 1


def test_fix_m4_stale_answers_do_not_move_the_plan():
    drv = _loop(ScriptedCoupleAstra([answer("continue", segment=D)], latency_s=16.0), 34.0)
    plans = [r["plan"] for r in drv.log if r["type"] == "answer"]
    assert plans == ["plan_stale", "plan_stale"] and drv.layer.plan is None
    assert drv.segment_intent() == SEGMENT_UNKNOWN
