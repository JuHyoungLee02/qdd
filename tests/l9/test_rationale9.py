"""L9 v2 build-time "why" (owner 10-02 22:40, L9_PRINCIPLES.md §2): one rationale clause per derivable cause, one
fixed template family, parse-back consistency gate (specgate9.rationale_mismatches)."""
import json

from harvest.l9 import rationale9 as RT
from harvest.l9 import specgate9 as SG

OBJ = "l9o_can"
META_TWO_ARM = {
    "robot": "ffw_sg2", "arm": "right",
    "objects": {OBJ: {"name": "metallic can", "node": "n0_top"}},
    "grasp_v2": {"picks": [{"obj": OBJ, "category": "beverage can metallic can", "part": "body", "family": "side",
                            "rot_bin_img": 2, "width_m": 0.0254, "open_bin3": "narrow", "approach_reason": "natural"}]},
}
META_FRANKA = dict(META_TWO_ARM, robot="franka_mast")
ROW = {"tgt": OBJ, "place": "s9_0"}


def _answer(arm="right", approach="side", rot=2, mode="point"):
    return {"assessment": {"evidence_view": "head"}, "command": {"mode": mode, "approach": approach, "rot": rot,
            "arm": arm, "point_2d": [1, 2]}, "reason": "Next: grasp the can."}


def test_two_armed_robot_gets_arm_clause_from_object_side():
    text = RT.build(META_TWO_ARM, ROW, _answer())
    assert text is not None
    assert text.startswith("right arm: the metallic can is on the robot's right")


def test_single_arm_robot_omits_arm_clause():
    text = RT.build(META_FRANKA, ROW, _answer())
    assert text is not None and "right arm:" not in text and "left arm:" not in text
    assert "side grasp on the body" in text  # the grasp clauses still fire


def test_approach_and_rot_clauses_from_matching_pick():
    text = RT.build(META_TWO_ARM, ROW, _answer())
    assert "side grasp on the body: it's narrow" in text
    assert "rot 2: pads across its 2.5 cm width" in text


def test_no_matching_pick_omits_grasp_clauses():
    bad_row = dict(ROW, tgt="l9o_other")  # no pick for this object
    ap, rc = RT.grasp_clauses(META_TWO_ARM, bad_row, _answer()["command"])
    assert ap is None and rc is None


def test_mismatched_rot_omits_grasp_clauses():
    ap, rc = RT.grasp_clauses(META_TWO_ARM, ROW, dict(_answer()["command"], rot=5))  # no pick at rot 5
    assert ap is None and rc is None


def test_build_returns_none_without_any_derivable_clause():
    meta = {"robot": "franka_mast", "objects": {}, "grasp_v2": {"picks": []}}
    cmd = {"mode": "stop"}
    assert RT.build(meta, {"tgt": "x"}, {"command": cmd}) is None


def test_inject_places_rationale_before_reason_and_after_command():
    ans = json.dumps(_answer())
    out = json.loads(RT.inject(ans, "right arm: test"))
    keys = list(out.keys())
    assert keys.index("command") < keys.index("rationale") < keys.index("reason")
    assert out["rationale"] == "right arm: test"


def test_strip_is_inverse_of_inject():
    ans = json.dumps(_answer())
    on = RT.inject(ans, "right arm: test")
    off = RT.strip(on)
    assert json.loads(off) == json.loads(ans)
    assert RT.strip(off) == off  # idempotent (no "rationale" key to remove)


def test_parse_roundtrip_matches_build():
    text = RT.build(META_TWO_ARM, ROW, _answer())
    got = RT.parse(text)
    assert got["arms"] == ["right"] and got["approach"] == "side" and got["rot"] == 2
    assert not got["handover"] and got["axis"] is None


def test_handover_clause_only_when_commanded():
    cmd = {"mode": "eef", "handover_point": [500, 500], "handover_height": "lift"}
    assert RT.handover_clause(cmd) == "handover: reachable by both arms, between them, lift height"
    assert RT.handover_clause({"mode": "eef"}) is None


def test_axis_clause_linear_and_rotary():
    assert RT.axis_clause({"mode": "point", "axis": "linear"}) == "axis linear: it slides along a straight track"
    assert RT.axis_clause({"mode": "point", "axis": "rotary", "turn": "cw"}) == "axis rotary cw: it turns about a hinge"
    assert RT.axis_clause({"mode": "point"}) is None


def test_schema_errors_accepts_valid_rationale_and_flags_bad_type():
    ans = dict(_answer(), rationale="right arm: the can is on the robot's right")
    assert SG.schema_errors(json.dumps(ans)) == []
    bad = dict(_answer(), rationale=123)
    assert any("rationale" in e for e in SG.schema_errors(json.dumps(bad)))


def test_rationale_mismatches_zero_for_consistent_rows():
    ans = _answer()
    ans["rationale"] = RT.build(META_TWO_ARM, ROW, ans)
    rows = [{"answer": json.dumps(ans)}]
    assert SG.rationale_mismatches(rows) == 0


def test_rationale_mismatches_catches_wrong_arm_word():
    ans = _answer()
    ans["rationale"] = "left arm: the can is on the robot's right; side grasp on the body: it's narrow; rot 2: pads across its 2.5 cm width"
    rows = [{"answer": json.dumps(ans)}]
    assert SG.rationale_mismatches(rows) == 1


def test_rationale_mismatches_catches_wrong_rot_number():
    ans = _answer()
    ans["rationale"] = "right arm: the can is on the robot's right; side grasp on the body: it's narrow; rot 9: pads across its 2.5 cm width"
    rows = [{"answer": json.dumps(ans)}]
    assert SG.rationale_mismatches(rows) == 1


def test_rationale_mismatches_skips_rows_without_rationale():
    rows = [{"answer": json.dumps(_answer())}]
    assert SG.rationale_mismatches(rows) == 0


def test_gates_reports_rationale_mismatches_key():
    ans = _answer()
    ans["rationale"] = RT.build(META_TWO_ARM, ROW, ans)
    rows = [{"answer": json.dumps(ans), "spec_version": SG.SPEC, "prompt_path": "p"}]
    g = SG.gates(rows, {"p": "x"})
    assert g["rationale_mismatches"] == 0 and g["ok"]
