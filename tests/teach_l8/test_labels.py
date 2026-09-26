"""Truth labels in the astra-solo@v2 schema: the clean plan, the three recovery rules, templated assessment that only
cites measured text, and answers the runtime validator accepts unchanged."""
import json

import numpy as np

from harvest.astra_motion.harness import obj_height
from harvest.astra_solo import schema as SC
from harvest.teach_l8 import labels as L

TZ, W_OPEN = 0.85, 0.107
INFO = {"tgt": "o3", "place": "o5", "present": ["o3", "o5"], "instruction": "Put the red mug on the blue tray."}
MUG = np.array([0.42, -0.20, TZ + obj_height("o3") / 2])
TRAY = np.array([0.44, -0.38, TZ + obj_height("o5") / 2])
GZ = TZ + obj_height("o3") - 0.018


def st(tcp, grip=W_OPEN, hold=False, on=False, upright=True, mug=MUG):
    return {"tcp": np.asarray(tcp, float), "grip_w": grip, "obj": {"o3": np.asarray(mug, float), "o5": TRAY},
            "pred": {"holding(o3)": hold, "on(o3,o5)": on, "upright(o3)": upright}}


def test_start_goes_above_target_and_validates():
    lab = L.label(st([0.34, -0.25, TZ + 0.25]), INFO, TZ, W_OPEN, first=True)
    assert lab["step"] == "above_target" and lab["phase"] == "approach" and lab["status"] == "not_started"
    c = lab["command"]
    assert c["mode"] == "eef" and c["gripper"] == "keep"
    assert np.allclose(c["position_m"], [0.42, -0.20, round(GZ + 0.10, 3)], atol=1e-3)
    parsed, err = SC.validate(lab["answer"])
    assert not err and parsed["command"]["position_m"] == c["position_m"]


def test_above_target_descends_and_closes():
    lab = L.label(st([0.425, -0.205, GZ + 0.10]), INFO, TZ, W_OPEN, first=False)
    assert lab["step"] == "descend_close" and lab["command"]["gripper"] == "close"
    assert np.allclose(lab["command"]["position_m"], [0.42, -0.20, GZ], atol=1e-3)


def test_low_and_off_target_lifts_first():
    lab = L.label(st([0.50, -0.10, TZ + 0.06]), INFO, TZ, W_OPEN, first=False)
    assert lab["step"] == "lift_clear"
    assert np.allclose(lab["command"]["position_m"], [0.50, -0.10, GZ + 0.10], atol=1e-3)


def test_empty_close_reopens_and_is_failed():
    lab = L.label(st([0.46, -0.20, GZ], grip=0.03), INFO, TZ, W_OPEN, first=False)
    assert lab["step"] == "reopen" and lab["command"] == {"mode": "gripper", "gripper": "open"}
    assert lab["status"] == "failed" and lab["phase"] == "approach"
    a = json.loads(lab["answer"])["assessment"]
    assert "nothing between the pads" in a["evidence"] and "3.0 cm" in a["evidence"]


def test_recovered_after_failure_and_blocked_is_failed():
    s = st([0.34, -0.25, TZ + 0.25])
    assert L.label(s, INFO, TZ, W_OPEN, first=False, prev_failed=True)["status"] == "recovered"
    b = L.label(s, INFO, TZ, W_OPEN, first=False, last_line="3: eef to (...) -> BLOCKED: stopped 40 mm")
    assert b["status"] == "failed" and "blocked" in json.loads(b["answer"])["assessment"]["evidence"]


def test_carry_chain():
    mug_held = [0.42, -0.20, GZ + 0.018 - obj_height("o3") / 2 + 0.01]
    up = L.label(st([0.42, -0.20, GZ + 0.01], grip=0.05, hold=True, mug=mug_held), INFO, TZ, W_OPEN, first=False)
    assert up["step"] == "carry_up" and np.allclose(up["command"]["position_m"], [0.42, -0.20, TZ + 0.22], atol=1e-3)
    assert json.loads(up["answer"])["assessment"]["task_progress"]["verified_completed"] == ["grasp the red mug"]
    over = L.label(st([0.42, -0.20, TZ + 0.22], grip=0.05, hold=True), INFO, TZ, W_OPEN, first=False)
    assert over["step"] == "carry_over" and over["command"]["gripper"] == "keep"
    assert np.allclose(over["command"]["position_m"][:2], TRAY[:2], atol=1e-3)
    tcp = np.array([0.44, -0.38, TZ + 0.22])
    mug = tcp + [0, 0, -0.03]
    put = L.label(st(tcp, grip=0.05, hold=True, mug=mug), INFO, TZ, W_OPEN, first=False)
    assert put["step"] == "lower_open" and put["command"]["gripper"] == "open" and put["phase"] == "carry"
    want = TZ + obj_height("o5") + (tcp[2] - (mug[2] - obj_height("o3") / 2)) + 0.004
    assert abs(put["command"]["position_m"][2] - want) < 1e-3


def test_after_release_retreats_up_then_stops():
    """Prompt: open, then move up about 10 cm, then stop."""
    tray_mug = np.array([0.44, -0.38, TZ + obj_height("o5") + obj_height("o3") / 2])
    low = st([0.44, -0.38, TZ + 0.10], on=True, mug=tray_mug)
    r = L.label(low, INFO, TZ, W_OPEN, first=False)
    assert r["step"] == "retreat" and r["command"]["gripper"] == "keep"
    assert np.allclose(r["command"]["position_m"], [0.44, -0.38, TZ + 0.20], atol=1e-3)
    high = st([0.44, -0.38, TZ + 0.25], on=True, mug=tray_mug)
    assert L.label(high, INFO, TZ, W_OPEN, first=False)["step"] == "done"


def test_stuck_rule():
    prev = {"mode": "eef", "position_m": [0.421, -0.357, 1.07], "gripper": "keep"}
    assert L.stuck("8: eef ... -> BLOCKED: stopped 111 mm", prev, dict(prev))
    assert not L.stuck("8: eef ... -> reached the target", prev, dict(prev))
    other = dict(prev, position_m=[0.30, -0.357, 1.07])
    assert not L.stuck("8: -> BLOCKED: stopped 111 mm", prev, other)
    assert not L.stuck("8: -> BLOCKED", None, prev)


def test_done_is_stop_and_tipped_has_no_label():
    d = L.label(st([0.44, -0.38, TZ + 0.2], on=True), INFO, TZ, W_OPEN, first=False)
    assert d["command"] == {"mode": "stop"} and d["step"] == "done"
    assert SC.validate(d["answer"])[1] == []
    assert L.label(st([0.3, -0.2, TZ + 0.2], upright=False), INFO, TZ, W_OPEN, first=False) is None


def test_marker_place_has_table_height():
    info = dict(INFO, place="o11")
    assert L.place_top("o11", TZ) == TZ and L.place_top("o5", TZ) > TZ
    s = st([0.34, -0.25, TZ + 0.25])
    s["obj"]["o11"] = np.array([0.44, -0.38, TZ + 0.001])
    s["pred"] = {"holding(o3)": False, "on(o3,o11)": False, "upright(o3)": True}
    assert L.label(s, info, TZ, W_OPEN, first=True)["step"] == "above_target"
