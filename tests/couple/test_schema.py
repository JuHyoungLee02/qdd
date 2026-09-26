import json
import re

import numpy as np
import pytest

from harvest.couple.mock import answer
from harvest.couple.params import CoupleParams
from harvest.couple.prompt import PROMPT_ID, build_input, request_from_input
from harvest.couple.schema import COMMANDS, CONFIDENCE, EDIT_MAX_M, EXEC_STATUS, GRIPPER, INTENT_STATUS, ROT_MAX_RAD, \
    SchemaError, parse_answer

CAMS = ("cam_head", "cam_wrist_left", "cam_wrist_right")


def _parse(d, mode="F0", cams=CAMS, t_state=1.0, t_deliver=4.5):
    return parse_answer("model says: " + json.dumps(d) + " end", mode, cams, 7, t_state, t_deliver)


def test_f0_edit_parses_with_age_and_views():
    a = _parse(answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.03, 0.0)))
    assert a.command == "edit" and a.request_no == 7 and a.diff is None
    assert a.age == pytest.approx(3.5)
    np.testing.assert_allclose(a.edit.dp, [0.0, 0.03, 0.0])
    np.testing.assert_allclose(a.edit.vec6(), [0.0, 0.03, 0.0, 0.0, 0.0, 0.0])
    assert a.edit.gripper == "keep" and a.evidence_views == ("cam_wrist_right",) and a.gate == "raw"


def test_edit_over_5cm_or_035rad_is_refused():
    with pytest.raises(SchemaError, match="delta_position_m"):
        _parse(answer("edit", execution="failed", dp=(0.04, 0.04, 0.0)))
    with pytest.raises(SchemaError, match="delta_rotation_rad"):
        _parse(answer("edit", execution="failed", dp=(0.0, 0.0, 0.01), dr=(0.0, 0.0, 0.4)))
    assert EDIT_MAX_M == 0.05 and ROT_MAX_RAD == 0.35


def test_views_and_claims_must_be_cameras_that_were_sent():
    with pytest.raises(SchemaError, match="evidence_views"):
        _parse(answer(views=("cam_wrist_left",)), cams=("cam_head", "cam_wrist_right"))
    with pytest.raises(SchemaError, match="claims"):
        _parse(answer(claims=(("grasped", "cam_wrist_left"),)), cams=("cam_head", "cam_wrist_right"))
    with pytest.raises(SchemaError, match="claims"):
        _parse(answer(claims=(("holding_tight", "cam_wrist_right"),)))


def test_edit_block_only_with_command_edit():
    d = answer("continue")
    d["edit"] = {"delta_position_m": [0, 0, 0.01], "delta_rotation_rad": [0, 0, 0], "gripper": "keep"}
    with pytest.raises(SchemaError, match="only with command edit"):
        _parse(d)


def test_f1_keep_and_revise():
    a = _parse(answer(diff="keep"), mode="F1")
    assert a.diff == "keep" and a.command == "continue" and a.edit is None
    b = _parse(answer("edit", diff="revise", execution="failed", dp=(0.0, 0.0, 0.02)), mode="F1")
    assert b.diff == "revise" and b.command == "edit"
    with pytest.raises(SchemaError, match="diff"):
        _parse(answer("continue"), mode="F1")


def test_garbage_and_bad_enums_are_schema_errors():
    with pytest.raises(SchemaError, match="no JSON"):
        parse_answer("I would continue.", "F0", CAMS, 1, 0.0, 3.0)
    with pytest.raises(SchemaError, match="confidence"):
        _parse(answer(confidence="very"))
    with pytest.raises(SchemaError, match="info_request"):
        _parse(answer(info="tilt_wrist"))


def test_params_guard_effort_and_mode():
    CoupleParams()
    with pytest.raises(ValueError, match="low"):
        CoupleParams(effort="high")
    with pytest.raises(ValueError, match="request_mode"):
        CoupleParams(request_mode="F2")
    with pytest.raises(ValueError, match="single_weight"):
        CoupleParams(single_weight=1.5)
    assert CoupleParams().to_json()["cameras"] == list(CAMS)


def test_params_probe_defaults():
    # canon §86 supplement (docs/design/00-interfaces.md), results docs/stage3/results/astra_motion.md §2/§5/§9:
    # these six fields are filled from the probe, not placeholders any more. A later edit must not silently
    # revert them (plan 2026-09-26 Task 1 controller ruling).
    p = CoupleParams()
    assert p.request_mode == "F0"
    assert p.stale_edit_s == pytest.approx(15.0)
    assert p.timeout_s == pytest.approx(20.0)
    assert p.latency_init_s == pytest.approx(9.3)
    assert p.est_text_tokens == 1601
    assert p.overlay is True
    assert p.probe_ref == "docs/stage3/results/astra_motion.md"


def test_prompt_roundtrip_and_image_labels():
    req = {"request_no": 3, "events": ["m7_critic_alarm"], "flow_state": {"last_command": {"command": "continue"}}}
    imgs = {"cam_head": b"\xff\xd8head", "cam_wrist_right": b"\xff\xd8wrist"}
    inp = build_input(req, imgs, CoupleParams(), "Put the red mug on the blue tray.")
    assert request_from_input(inp) == req
    content = inp[0]["content"]
    assert [c["text"] for c in content[1:] if c["type"] == "input_text"] == ["cam_head:", "cam_wrist_right:"]
    assert sum(1 for c in content if c["type"] == "input_image") == 2
    assert "cam_wrist_right" in content[0]["text"] and "0.05" in content[0]["text"]
    assert all(re.fullmatch(r"[0-9a-f]{12}", v) for v in PROMPT_ID.values()) and PROMPT_ID["F0"] != PROMPT_ID["F1"]


def test_vocabulary_matches_the_probe_when_it_is_importable():
    S = pytest.importorskip("harvest.astra_motion.schema")
    assert set(S.GRIPPER) == set(GRIPPER) and tuple(S.EXEC_STATUS) == EXEC_STATUS
    assert tuple(S.INTENT_STATUS) == INTENT_STATUS and tuple(S.CONFIDENCE) == CONFIDENCE
    assert tuple(S.DECISIONS) == COMMANDS
    assert S.EDIT_MAX_CM / 100.0 == pytest.approx(EDIT_MAX_M) and S.ROT_MAX_RAD == pytest.approx(ROT_MAX_RAD)
