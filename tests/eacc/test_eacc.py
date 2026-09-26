"""E-ACC tools (tools/eacc): v2 prompt text and parser, arm parsing, bench oracle and scoring, pre-registered
decision rules, and the runner end to end with a mock client on a synthetic two-snapshot bench (no Isaac, no
network)."""
import importlib.util
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "eacc"))

import arms as A  # noqa: E402
import bench as B  # noqa: E402
import prompt_v2 as P2  # noqa: E402
import score as S  # noqa: E402

from harvest.couple import prompt as CP  # noqa: E402
from harvest.serialize import SEGMENT_ACTIONS, SEGMENTS  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = _load("ph_variants_eacc", ("tools", "prompt_health", "variants.py"))

ANS_V2 = {"assessment": {"task_progress": {"verified_completed": [], "currently_attempting": "reach mug",
                                           "remaining": ["grasp"]},
                         "execution": "progressing", "intent": "misaligned", "confidence": "high",
                         "evidence": "tip heads left of the mug", "evidence_views": ["cam_head"], "claims": []},
          "segment": {"now": "approach", "do": "none", "next": "descend"}, "command": "edit",
          "edit": {"delta_position_m": [0.03, 0.0, 0.0], "delta_rotation_rad": [0, 0, 0], "gripper": "keep",
                   "valid_until": "next_answer"}, "info_request": "none"}


# ------------------------------------------------------------------------------------------ prompt v2
def test_v2_reuses_prompt_health_definitions():
    assert P2.DEFS == V.COUPLE_DEFS
    assert P2.FRAME == V.COUPLE_FRAME


def test_v2_answer_form_vocabulary_matches_serializer():
    for s in SEGMENTS:
        assert s in P2.ANSWER_FORM
    for s in SEGMENT_ACTIONS:
        assert s in P2.ANSWER_FORM
    assert "0.04" in P2.COMMANDS and "0.05" not in P2.COMMANDS


def test_legend_only_drawn_elements():
    t = P2.legend_text({"head": {"ring", "axes"}, "wrist": set()}, 2.5)
    assert "white ring" in t and "red / green / blue" in t
    assert "FILLED head" not in t and "DASHED" not in t and "cyan" not in t
    t2 = P2.legend_text({"head": {"ring", "trace", "next", "axes"}, "wrist": {"next"}}, 2.5)
    assert "executed motion" in t2 and "cyan solid arrow" in t2 and "magenta" not in t2
    assert P2.legend_text(None, 2.5) == "No overlay is drawn on the images.\n"


def test_events_legend_selected_by_request():
    assert P2.events_text([]) == ""
    t = P2.events_text([{"t": 1.0, "event": "no_progress"}, "m7_critic_alarm"])
    assert "no_progress =" in t and "m7_critic_alarm =" in t and "layer_mismatch" not in t


def test_camera_text_names_only_sent_cameras():
    t3 = P2.camera_text(list(A.CAMS3))
    t2 = P2.camera_text(list(A.CAMS2))
    assert "cam_wrist_left" in t3 and "cam_wrist_left" not in t2 and "(cam_wrist_right)" in t2


def test_campose_text_uses_columns():
    R = [[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]]  # optical: right = -y, down = -z, forward = +x
    t = P2.campose_text({"cam_head": {"R": R, "t": [0.1, 0.0, 1.5]}}, ["cam_head"], 0.183)
    assert "looking along (+1.00, +0.00, +0.00)" in t and "image right = (+0.00, -1.00, +0.00)" in t
    assert "image down = (+0.00, +0.00, -1.00)" in t and "0.18 m above the table" in t


def test_parse_v2_valid_and_invalid():
    a, seg, vu = P2.parse_v2(json.dumps(ANS_V2), ["cam_head", "cam_wrist_right"])
    assert a.command == "edit" and seg == {"now": "approach", "do": "none", "next": "descend"} and vu == "next_answer"
    bad = json.loads(json.dumps(ANS_V2))
    bad["segment"]["now"] = "grasping"
    bad["edit"]["valid_until"] = "forever"
    with pytest.raises(P2.V2Error) as e:
        P2.parse_v2(json.dumps(bad), ["cam_head"])
    assert any("segment" in p for p in e.value.problems) and any("valid_until" in p for p in e.value.problems)
    over = json.loads(json.dumps(ANS_V2))
    over["edit"]["delta_position_m"] = [0.045, 0.0, 0.0]  # above the stated 0.04, inside the 0.05 tolerance
    assert P2.parse_v2(json.dumps(over), ["cam_head"])[0].command == "edit"


def test_parse_v2_continue_needs_no_valid_until():
    d = json.loads(json.dumps(ANS_V2))
    d["command"], d["edit"] = "continue", None
    a, seg, vu = P2.parse_v2(json.dumps(d), ["cam_head"])
    assert a.command == "continue" and vu is None


# ------------------------------------------------------------------------------------------ arms
def test_parse_arm():
    a = A.parse_arm("v2cp_med_2cam")
    assert a["effort"] == "medium" and a["cams"] == A.CAMS2 and a["campose"] and a["context"]
    assert A.parse_arm("v1")["context"] is False
    assert A.parse_arm("v2_r1")["rep"] == 1
    for bad in ("v3", "v1_2cam", "v2_med_med", "v2_x"):
        with pytest.raises(ValueError):
            A.parse_arm(bad)


# ------------------------------------------------------------------------------------------ bench / oracle
def _path(points, phases, t0=0.0, dt=0.05, holding=False):
    out = []
    for i, (p, ph) in enumerate(zip(points, phases)):
        out.append({"t": round(t0 + i * dt, 3), "tip": list(map(float, p)), "phase": ph, "grip_w": 0.107,
                    "holding": holding})
    return out


def _meta(kind="off_a", n=400, t_snap=2.0, tip_end=(0.40, -0.10, 1.00)):
    """Straight path from start to tip_end over n ticks (20 Hz); the oracle target at (0.45, -0.20)."""
    start = np.array([0.30, -0.25, 1.05])
    end = np.array(tip_end)
    pts = [start + (end - start) * min(1.0, i / 60) for i in range(n)]
    phases = ["approach"] * n if kind != "on" else (["approach"] * 40 + ["descend"] * 60 + ["close"] * 20
                                                    + ["lift"] * 60 + ["carry"] * 220)[:n]
    path = _path(pts, phases)
    tip = B.at(path, t_snap)["tip"]
    cam = {"name": "head", "W": 64, "H": 48, "fx": 50.0, "fy": 50.0, "cx": 32.0, "cy": 24.0,
           "R": [[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]], "t": [0.0, -0.2, 1.1]}
    return {"id": f"{kind}_00", "kind": kind, "seed": 16, "task": "mug_tray", "on_phase": "approach" if kind == "on" else None,
            "instruction": "Put the red mug on the blue tray.", "tgt": "o3", "place": "o5", "table_z": 0.80,
            "delta": [0.0, 0.08, 0.0], "wrong_goal": list(tip_end),
            "oracle": {"target_c": [0.45, -0.20, 0.85], "pregrasp": [0.45, -0.20, 0.995],
                       "grasp_point": [0.45, -0.20, 0.877], "place_xy": [0.40, -0.40]},
            "t_snap": t_snap, "tip": tip, "grip_w": 0.107, "holding": False,
            "cams": {c: dict(cam, name=c) for c in A.CAMS3}, "path": path, "tip_start": path[0]["tip"]}


def test_oracle_off_direction_and_segment():
    m = _meta()
    o = B.oracle(m)
    assert o["expected"] == ["edit"] and o["segments"] == ["approach"]
    tip_a = np.array(B.at(m["path"], m["t_snap"] + B.L_ARR)["tip"])
    assert np.allclose(np.array(o["dir_arr"]), np.array(m["oracle"]["pregrasp"]) - tip_a, atol=1e-4)
    good = B.score_answer(m, {"command": "edit", "command_raw": "edit", "edit_dp": [0.02, -0.04, 0.0],
                              "segment": {"now": "approach", "do": "none", "next": "descend"}})
    assert good["dir_ok"] and good["cmd_ok"] and good["seg_ok"] and good["triple_ok"]
    wrong = B.score_answer(m, {"command": "edit", "command_raw": "edit", "edit_dp": [-0.03, 0.03, 0.0],
                               "segment": {"now": "approach", "do": "close", "next": "descend"}})
    assert not wrong["dir_ok"] and wrong["seg_ok"] and not wrong["triple_ok"]
    cont = B.score_answer(m, {"command": "continue", "command_raw": "continue", "edit_dp": None, "segment": None})
    assert cont["dir_ok"] is False and cont["cmd_ok"] is False and cont["seg_ok"] is None
    inv = B.score_answer(m, None)
    assert inv["dir_ok"] is False and inv["cmd_ok"] is False and inv["seg_ok"] is False


def test_oracle_on_segments_send_or_arrival():
    m = _meta("on", t_snap=1.0)
    o = B.oracle(m)
    assert o["expected"] == ["continue"] and set(o["segments"]) == {"approach", "carry"}
    assert o["dir_arr"] is None


def test_subgoal_switches_to_grasp_point_below_pregrasp():
    m = _meta()
    assert np.allclose(B.subgoal(m, [0.40, -0.10, 1.00]), m["oracle"]["pregrasp"])
    assert np.allclose(B.subgoal(m, [0.40, -0.10, 0.90]), m["oracle"]["grasp_point"])
    mc = dict(m, kind="off_c")
    assert np.allclose(B.subgoal(mc, [0.30, -0.30, 1.0]), [0.40, -0.40, 1.0])


def test_committed_decision_and_token_vec():
    c = B.committed_decision([0, 0, 0], [0.02, 0.0, -0.01])
    assert c == {"dir_xy": "plus_x", "dir_z": "down", "mag_coarse": "medium"}
    v = B.token_vec(c)
    assert np.isclose(np.linalg.norm(v), 0.02) and v[0] > 0 and v[2] < 0


def test_plan_fixed_and_dev_only():
    p = B.plan()
    ids = [e["id"] for e in p]
    assert len(ids) == len(set(ids)) == 38
    assert all(0 <= e["seed"] <= 29 for e in p)
    assert sum(e["kind"] == "on" for e in p) == 12
    assert B.plan() == p


def test_request_v1_fields_and_v2_context():
    m = _meta(t_snap=12.0)
    r1 = B.request(m, list(A.CAMS3), version="v1", next_vec=None, context=True)
    assert "since_last_request" not in r1 and r1["schema"] == "astra-couple@v1"
    r2 = B.request(m, list(A.CAMS3), version="v2", next_vec=[0.01, 0, 0], context=True)
    s = r2["since_last_request"]
    assert s["previous_request"]["command"] == "continue" and s["previous_request"]["age_s"] == B.L_ARR
    early = B.request(_meta(t_snap=2.0), list(A.CAMS3), version="v2", next_vec=None, context=True)
    assert early["since_last_request"]["previous_request"] is None


# ------------------------------------------------------------------------------------------ images / build (no Isaac)
def _bench(tmp_path):
    from PIL import Image
    root = tmp_path / "bench"
    for kind in ("off_a", "on"):
        m = _meta(kind, t_snap=2.0 if kind == "off_a" else 1.0)
        m["id"] = {"off_a": "off_a_00", "on": "on_00"}[kind]
        m["checks"] = {"ok": True}
        d = root / m["id"]
        d.mkdir(parents=True)
        for c in A.CAMS3:
            Image.fromarray((np.random.default_rng(0).random((48, 64, 3)) * 255).astype(np.uint8)).save(d / f"{c}.png")
        (d / "meta.json").write_text(json.dumps(m))
    return root


def test_build_every_arm(tmp_path):
    root = _bench(tmp_path)
    m = json.loads((root / "off_a_00" / "meta.json").read_text())
    for name in ("v1", "v2", "v2cp", "v2_2cam", "v2_noov", "v2_noctx", "v2cp_dlow"):
        arm = A.parse_arm(name)
        inp, req, pid, text = A.build(str(root / "off_a_00"), m, arm)
        n_img = sum(c.get("type") == "input_image" for c in inp[0]["content"])
        assert n_img == len(arm["cams"])
        if name == "v1":
            assert pid == CP.PROMPT_ID["F0"] and "segment" not in text.split(CP.REQ_OPEN)[0]
        else:
            assert pid == P2.PROMPT_ID and '"segment": {"now"' in text
            assert ("Camera poses now" in text) == arm["campose"]
            assert ("since_last_request (in the request)" in text) == arm["context"]
            assert ("No overlay is drawn" in text) == (not arm["overlay"])
        if arm["detail"]:
            assert all(c.get("detail") == arm["detail"] for c in inp[0]["content"] if c.get("type") == "input_image")


def test_runner_mock_and_score(tmp_path):
    import run_eacc as R
    root = _bench(tmp_path)
    out = tmp_path / "rows.jsonl"
    args = ["--bench", str(root), "--set", "screen", "--arms", "v1,v2,v2cp", "--model", "mock", "--out", str(out)]
    R.main(args)
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert len(rows) == 6 and all(r["valid"] for r in rows)
    R.main(args)  # resumable: nothing new
    assert len(out.read_text().splitlines()) == 6
    metas = S.load_metas(str(root))
    srows = S.scored(rows, metas)
    tab = S.arm_table(srows, metas)
    assert tab["v2"]["M3_command"]["n"] == 2 and tab["v1"]["M2_segment"]["n"] == 0
    dec = S.decide(srows, tab)
    assert "R1_v2_vs_v1" in dec and dec["R2_campose"]["verdict"] in ("adopt", "reject", "undecided")


def test_paired_bootstrap_counts():
    srows = []
    for i in range(10):
        for arm, ok in (("a", i < 3), ("b", i < 7)):
            srows.append({"arm": arm, "snap": f"s{i}", "kind": "off_a", "score": {"dir_ok": ok}})
    p = S.paired(srows, "a", "b", "dir_ok", ("off_a",))
    assert p["n"] == 10 and p["diff"] == 0.4 and p["b_only"] == 4 and p["a_only"] == 0 and p["ci95"][0] > 0
