"""Prompt health check scoring (tools/prompt_health/analyze.py) on synthetic rows."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


A = _load("ph_analyze", ("tools", "prompt_health", "analyze.py"))


def g(snap, variant, state, truth, temp=0.0, rep=0, valid=True, raw="x"):
    return {"test": "grasp", "model": "m", "snap": snap, "variant": variant, "temp": temp, "rep": rep,
            "valid": valid, "grasp_state": state if valid else None, "truth": truth, "raw": raw, "prompt_sha": "s"}


def test_grasp_flip_and_truth_rates():
    rows = [g("a", "base", "grasped", True), g("b", "base", "not_grasped", False), g("c", "base", "grasped", False),
            g("a", "nodef", "grasped", True), g("b", "nodef", "grasped", False), g("c", "nodef", None, False, valid=False)]
    res = A.score(rows)["grasp|m"]
    assert res["base"]["truth"]["false_grasped"] == {"k": 1, "n": 2, "rate": 0.5}
    assert res["nodef"]["flip_vs_base"]["grasp_state"] == {"k": 1, "n": 2, "rate": 0.5}
    assert res["nodef"]["parse_fail"]["k"] == 1
    assert res["nodef"]["truth"]["false_grasped"]["k"] == 1


def test_repeat_identical_text():
    rows = [g("a", "base", "grasped", True, raw="r1"), g("b", "base", "grasped", True, raw="r2"),
            g("a", "base", "grasped", True, rep=1, raw="r1"), g("b", "base", "grasped", True, rep=1, raw="zz")]
    res = A.score(rows)["grasp|m"]
    assert res["base@t0r1"]["identical_text_vs_rep0"]["k"] == 1


def test_frame_angles_and_signs():
    base = {"test": "frame", "model": "m", "snap": "a", "variant": "prod", "temp": 0.0, "rep": 0, "valid": True,
            "dp": [0.0, -0.05, 0.0], "truth": [0.0, 0.1, -0.05], "raw": "", "prompt_sha": "s"}
    fr = dict(base, variant="frame", dp=[0.0, 0.05, 0.0])
    res = A.score([base, fr])["frame|m"]
    assert res["prod"]["truth"]["y_sign_agree"]["k"] == 0
    assert res["frame"]["truth"]["y_sign_agree"]["k"] == 1
    assert res["frame"]["truth"]["xy_err_deg_median"] == 0.0
    assert res["frame"]["flip_vs_base"]["dir_flip_gt90_vs_base"]["k"] == 1


def test_angle_none_for_zero():
    assert A.angle_deg([0, 0, 1], [1, 0, 0]) is None
    assert round(A.angle_deg([1, 0], [0, 1])) == 90


def test_couple_truth_counts():
    r = {"test": "couple_g", "model": "m", "snap": "a", "variant": "base", "temp": 0.0, "rep": 0, "valid": True,
         "execution": "progressing", "intent": "aligned", "command": "continue", "command_raw": "edit",
         "claim_raw": "grasped", "claim_gated": "none", "gate": "no_takeover_reason", "truth": False, "raw": "",
         "prompt_sha": "s"}
    res = A.score([r])["couple_g|m"]["base"]["truth"]
    assert res["false_claim_raw"]["k"] == 1 and res["false_claim_gated"]["k"] == 0
    assert res["edit_raw"] == 1 and res["edit_after_gate"] == 0
    assert res["cmd_acc_raw"]["k"] == 0 and res["cmd_acc_gated"]["k"] == 1


def test_expected_command_and_miss_direction():
    miss = {"test": "couple_g", "model": "m", "snap": "a", "variant": "base", "temp": 0.0, "rep": 0, "valid": True,
            "execution": "failed", "intent": "aligned", "command": "edit", "command_raw": "edit", "claim_raw": "none",
            "claim_gated": "none", "gate": "ok", "truth": False, "state": "miss", "edit_dp": [0.03, 0.0, -0.01],
            "raw": "", "prompt_sha": "s"}
    held = dict(miss, snap="b", truth=True, command="continue", command_raw="continue", edit_dp=None)
    res = A.score([miss, held])["couple_g|m"]["base"]["truth"]
    assert res["cmd_acc_raw"]["k"] == 2 and res["miss_edit_dir_ok"] == {"k": 1, "n": 1, "rate": 1.0}
    assert A.expected_command("couple_r", {"state": "carry"}) == "continue"
