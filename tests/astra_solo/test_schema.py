"""Answer schema of the Astra-solo arm (GPT-as-Policy direct-control modes eef / edit + gripper / stop)."""
import json

from harvest.astra_solo import schema as S

A = {"task_progress": {"verified_completed": [], "currently_attempting": "approach the mug", "remaining": ["grasp"]},
     "execution_status": "progressing", "evidence": "head view: gripper above the table", "evidence_view": "head",
     "confidence": "medium"}


def ans(cmd, **kw):
    return json.dumps({"assessment": A, "command": cmd, "reason": "r", **kw})


def test_eef_absolute_target_parses():
    p, err = S.validate(ans({"mode": "eef", "position_m": [0.45, -0.2, 0.95], "gripper": "keep"}))
    assert err == [] and p["command"]["mode"] == "eef" and p["command"]["position_m"] == [0.45, -0.2, 0.95]


def test_edit_over_limit_is_scaled_not_rejected():
    p, err = S.validate(ans({"mode": "edit", "delta_m": [0.3, 0.0, 0.0], "gripper": "keep"}))
    assert err == [] and abs(p["command"]["delta_m"][0] - S.EDIT_MAX_M) < 1e-9 and p["command"]["scaled"] is True


def test_missing_gripper_on_a_move_means_keep_and_is_recorded():
    p, err = S.validate(ans({"mode": "eef", "position_m": [0.45, -0.2, 0.95]}))
    assert err == [] and p["command"]["gripper"] == "keep" and p["command"]["gripper_defaulted"] is True
    p, err = S.validate(ans({"mode": "edit", "delta_m": [0.0, 0.01, 0.0], "gripper": None}))
    assert err == [] and p["command"]["gripper"] == "keep"
    assert S.validate(ans({"mode": "eef", "position_m": [0.45, -0.2, 0.95], "gripper": "grab"}))[0] is None


def test_gripper_mode_needs_open_or_close():
    assert S.validate(ans({"mode": "gripper", "gripper": "close"}))[1] == []
    assert S.validate(ans({"mode": "gripper", "gripper": "keep"}))[0] is None


def test_stop_and_invalid_answers():
    assert S.validate(ans({"mode": "stop"}))[1] == []
    assert S.validate(ans({"mode": "teleport"}))[0] is None
    assert S.validate("go grab the mug")[0] is None
    assert S.validate(json.dumps({"command": {"mode": "stop"}}))[0] is None  # assessment missing
    assert S.validate(ans({"mode": "eef", "position_m": [0.4, "x", 1.0], "gripper": "keep"}))[0] is None


def test_fenced_json_is_accepted():
    p, err = S.validate("```json\n" + ans({"mode": "stop"}) + "\n```")
    assert err == [] and p["command"]["mode"] == "stop"
