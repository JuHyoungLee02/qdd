"""Typed JSON outputs of the S command interface (GPT-as-Policy style) and the flow-anchored diff (F1)."""
import json

import pytest

from harvest.astra_motion import schema as SC

TP = {"verified_completed": [], "currently_attempting": "reach the red mug", "remaining": ["grasp", "place"]}


def assess(ex="progressing", it="aligned", conf="medium"):
    return {"task_progress": TP, "current_subgoal": "approach the mug", "execution_status": ex,
            "execution_evidence": "head view: TCP moved toward the mug", "intent_status": it,
            "intent_evidence": "moving to mug", "confidence": conf}


def cmd(decision, **kw):
    d = {"assessment": assess(), "decision": decision, "reason": "because"}
    d.update(kw)
    return json.dumps(d)


EDIT = {"delta_position_cm": [3.0, -2.0, -1.0], "delta_rotation_rad": [0.0, 0.0, 0.1], "gripper": "keep"}


def test_extract_json_with_fences_and_text():
    t = 'Sure.\n```json\n{"a": 1, "b": {"c": 2}}\n```\nDone'
    assert SC.extract_json(t) == {"a": 1, "b": {"c": 2}}
    with pytest.raises(SC.SchemaError):
        SC.extract_json("no json here")


def test_continue_stop_edit():
    for dec in ("continue", "stop"):
        out, err = SC.validate("S-cmd", cmd(dec))
        assert err == [] and out["decision"] == dec and out["assessment"]["task_progress"] == TP
    out, err = SC.validate("S-cmd", cmd("edit", edit=EDIT))
    assert err == [] and out["edit"]["delta_position_cm"] == [3.0, -2.0, -1.0]
    assert out["edit"]["delta_rotation_rad"] == [0.0, 0.0, 0.1]


def test_edit_rotation_optional():
    e = {"delta_position_cm": [0, 0, -2], "gripper": "close"}
    out, err = SC.validate("S-cmd", cmd("edit", edit=e))
    assert err == [] and out["edit"]["delta_rotation_rad"] == [0.0, 0.0, 0.0]


@pytest.mark.parametrize("bad", [
    {"delta_position_cm": [4, 4, 0], "gripper": "keep"},  # 5.66 cm > 5 cm
    {"delta_position_cm": [0, 0, 1], "delta_rotation_rad": [0.3, 0.3, 0], "gripper": "keep"},  # 0.42 rad
    {"delta_position_cm": [0, 0], "gripper": "keep"},
    {"delta_position_cm": [0, 0, 1], "gripper": "grab"},
    None])
def test_edit_errors(bad):
    out, err = SC.validate("S-cmd", cmd("edit", edit=bad))
    assert out is None and err


def test_assessment_enums_and_decision():
    d = json.loads(cmd("continue"))
    d["assessment"]["execution_status"] = "great"
    out, err = SC.validate("S-cmd", json.dumps(d))
    assert out is None and any("execution_status" in e for e in err)
    out, err = SC.validate("S-cmd", cmd("eef"))
    assert out is None and any("decision" in e for e in err)
    d = json.loads(cmd("continue"))
    del d["assessment"]["task_progress"]
    assert SC.validate("S-cmd", json.dumps(d))[0] is None


def test_confidence_required_and_uncertain_flag():
    d = json.loads(cmd("continue"))
    del d["assessment"]["confidence"]
    assert SC.validate("S-cmd", json.dumps(d))[0] is None
    out, _ = SC.validate("S-cmd", json.dumps(dict(json.loads(cmd("edit", edit=EDIT)),
                                                  assessment=assess(conf="low"))))
    assert SC.is_uncertain(out) and not SC.is_uncertain(SC.validate("S-cmd", cmd("edit", edit=EDIT))[0])
    out, _ = SC.validate("S-cmd", json.dumps(dict(json.loads(cmd("edit", edit=EDIT)), assessment=assess(ex="uncertain"))))
    assert SC.is_uncertain(out)


def test_grasp_claims_need_wrist_evidence():
    a = assess()
    a["task_progress"] = {"verified_completed": ["approach mug", "grasp mug"], "currently_attempting": "lift",
                          "remaining": ["place"]}
    a["execution_evidence"] = "head view: fingers around the mug"
    out, err = SC.validate("S-cmd", json.dumps({"assessment": a, "decision": "continue"}))
    assert out is None and any("wrist" in e for e in err)
    a["execution_evidence"] = "right wrist view: mug between the pads, lifted"
    out, err = SC.validate("S-cmd", json.dumps({"assessment": a, "decision": "continue"}))
    assert err == [] and out["assessment"]["claims"] == ["grasp mug"]


def test_grasp_probe_schema():
    ok = {"grasp_state": "grasped", "evidence_view": "right_wrist", "evidence": "mug between pads",
          "confidence": "high"}
    out, err = SC.validate("G", json.dumps(ok))
    assert err == [] and out["grasp_state"] == "grasped"
    for bad in (dict(ok, grasp_state="maybe"), dict(ok, evidence_view="tail"), dict(ok, confidence=3)):
        assert SC.validate("G", json.dumps(bad))[0] is None


def test_flow_diff_keep_and_revise():
    base = {"assessment": assess(), "evidence": "on track"}
    out, err = SC.validate("S-diff", json.dumps(dict(base, decision="keep")))
    assert err == [] and out["decision"] == "keep"
    rev = dict(base, decision="revise", command={"decision": "edit", "edit": EDIT})
    out, err = SC.validate("S-diff", json.dumps(rev))
    assert err == [] and out["command"]["decision"] == "edit"
    out, err = SC.validate("S-diff", json.dumps(dict(base, decision="revise", command={"decision": "stop"})))
    assert err == [] and out["command"]["decision"] == "stop"
    for bad in (dict(rev, evidence=""), dict(base, decision="revise"), dict(base, decision="maybe"),
                dict(rev, command={"decision": "edit", "edit": {"delta_position_cm": [9, 0, 0], "gripper": "keep"}})):
        out, err = SC.validate("S-diff", json.dumps(bad))
        assert out is None and err, bad
