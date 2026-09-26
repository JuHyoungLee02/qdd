"""ser-A-min-3 intent inputs (plan 2026-09-26 Task 12): the §87 gripper decision question (label rule in one place with
boundaries, the fused DecCall question, stage-B items / expert conditioning slot, the S-E2E command label) and the §90
segment-intent line (vocabulary check, R2 phase rule, S-E2E gripper-event rule, place in the DecCall state)."""
import json

import pytest

from harvest import intent as G
from harvest.deccall_snap import build_snapshot_request


def test_rule_from_phase_close_open_else_keep():
    assert G.from_phase("close") == "close" and G.from_phase("open") == "open"
    for p in ("approach", "descend", "lift", "carry", "place_descend", "retreat", "done", None, "", "na"):
        assert G.from_phase(p) == "keep"
    assert G.KEYS == ("close", "open", "keep") and G.RATE_THR == 0.176


def test_rule_from_openness_strict_threshold_boundaries():
    # rate = (open_then - open_now) / window, openness per second (+ = opening); strict like the motion line bins
    assert G.from_openness(0.0, 0.176, 1.0) == "keep"  # exactly the threshold -> keep
    assert G.from_openness(0.0, 0.1761, 1.0) == "open"
    assert G.from_openness(0.176, 0.0, 1.0) == "keep"  # exactly -threshold -> keep
    assert G.from_openness(0.1761, 0.0, 1.0) == "close"
    assert G.from_openness(0.5, 0.5, 0.3) == "keep"
    assert G.from_openness(1.0, 0.0, 0.5) == "close" and G.from_openness(0.0, 1.0, 0.5) == "open"
    with pytest.raises(ValueError, match="window"):
        G.from_openness(0.0, 1.0, 0.0)


def test_segment_line_vocabulary_and_check():
    from harvest.serialize import SEGMENT_UNKNOWN, check_segment, segment_line
    assert segment_line("approach", "none", "grasp") == "segment: now=approach do=none next=grasp"
    assert check_segment(SEGMENT_UNKNOWN) == SEGMENT_UNKNOWN
    for bad in (("reach", "none", "grasp"), ("approach", "keep", "grasp"), ("approach", "none", "o3")):
        with pytest.raises(ValueError, match="segment value"):
            segment_line(*bad)
    for bad in ("segment: now=approach do=none", "segment now=approach do=none next=grasp",
                "segment: now=approach do=none next=grasp x=1"):
        with pytest.raises(ValueError, match="segment"):
            check_segment(bad)


def test_segment_rule_from_the_r2_phase_sequence():
    want = {"approach": "now=approach do=none next=descend", "descend": "now=descend do=none next=grasp",
            "close": "now=grasp do=close next=lift", "lift": "now=lift do=none next=carry",
            "carry": "now=carry do=none next=place", "place_descend": "now=place do=none next=release",
            "open": "now=release do=open next=retreat", "retreat": "now=retreat do=none next=done",
            "done": "now=done do=none next=done"}
    from harvest.sim.snapshot import PHASE_ORDER
    assert set(want) == set(PHASE_ORDER) == set(G.PHASE_SEGMENT)  # every planner phase maps 1:1
    for ph, s in want.items():
        assert G.segment_from_phase(ph) == "segment: " + s
    assert G.segment_from_phase("na") == G.segment_from_phase(None) == "segment: now=unknown do=unknown next=unknown"


def test_segment_rule_from_s_e2e_gripper_events():
    labs = ["keep", "keep", "close", "keep", "keep", "open", "keep", "close", "keep", "open", "keep"]
    got = [s[len("segment: "):] for s in G.segments_from_events(labs)]
    assert got == ["now=approach do=none next=grasp", "now=approach do=none next=grasp",
                   "now=grasp do=close next=carry", "now=carry do=none next=release",
                   "now=carry do=none next=release", "now=release do=open next=approach",
                   "now=approach do=none next=grasp", "now=grasp do=close next=carry",
                   "now=carry do=none next=release", "now=release do=open next=retreat",
                   "now=retreat do=none next=unknown"]
    assert G.segments_from_events(["keep", "keep"]) == ["segment: now=unknown do=unknown next=unknown"] * 2
    assert G.segments_from_events(["close", "keep"])[1] == "segment: now=carry do=none next=unknown"  # no release
    assert G.segments_from_events([]) == []
    got = G.segments_from_events(["keep", None, "close"])  # None = not derivable: unknown, and no event
    assert got[0].endswith("now=approach do=none next=grasp") and got[1] == G.SEGMENT_UNKNOWN
    assert got[2].endswith("now=grasp do=close next=carry")


def test_deccall_state_tail_order_segment_motion_last_step():
    req, _, _ = build_snapshot_request(_line("close"))
    assert req["state"].split("\n")[-3:] == ["segment: now=grasp do=close next=lift",
                                             "motion: arm=unknown gripper=unknown", "last_step: none"]
    seg = "segment: now=approach do=none next=grasp"  # an explicit line (runtime: Astra's plan) wins over the rule
    req, _, _ = build_snapshot_request({**_line("close"), "segment": seg})
    assert req["state"].split("\n")[-3] == seg
    with pytest.raises(ValueError, match="segment"):
        build_snapshot_request({**_line("close"), "segment": "segment: now=reach do=none next=grasp"})


def _line(phase="carry"):
    return {"seed": 0, "kind": "P0", "k": 21, "ds_id": "ds21", "phase": phase, "text_state": "t_state: f1\nrobot: x",
            "state": {"present": ["o3", "o5"]},
            "oracle": {"dir_xy": "plus_y", "dir_z": "none_z", "mag_coarse": "large", "target": "o5",
                       "phase_choice": "continue", "progress": "valid_progress"}}


def test_deccall_gripper_question_only_when_asked_and_after_phase():
    req, oracle, _ = build_snapshot_request(_line())
    assert "ds21.gripper" not in req["questions"]  # the modular (Jev-L) DecCall keeps its five + progress questions
    req, oracle, shown = build_snapshot_request(_line("close"), fused=True)
    assert list(req["questions"]) == ["ds21.dir_xy", "ds21.dir_z", "ds21.mag_coarse", "ds21.target", "ds21.phase",
                                      "ds21.gripper", "mon.progress"]
    assert list(req["questions"]["ds21.gripper"]["criteria"]) == ["close", "open", "keep", "NONE_ESCALATE"]
    assert oracle["ds21.gripper"] == "close" and shown["ds21.gripper"][0] == "gripper"
    assert build_snapshot_request(_line("lift"), fused=True)[1]["ds21.gripper"] == "keep"


def _fused_desc(q):
    req, _, _ = build_snapshot_request(_line("descend"), fused=True)
    return req["questions"][f"ds21.{q}"]


def test_fused_dir_xy_and_mag_text_state_the_label_definitions():
    """Ruling PH-A1: the fused wording describes the labels_v2 definition (remaining offset to the sub-goal, per-axis
    sign with the 1 cm dead band; |d| binned by MAG_EDGES_M); labels are unchanged."""
    from harvest.labels_v2 import dir_xy_label, mag_label
    xy, mag = _fused_desc("dir_xy"), _fused_desc("mag_coarse")
    assert "sign pattern of the remaining horizontal offset" in xy["instructions"]
    assert "3D distance" in mag["instructions"] and "sub-goal" in mag["instructions"]
    table = [  # remaining offset d (m) -> label -> the option text that must describe it
        ((0.03, 0.0, 0.0), "plus_x", "x at least 1.00 cm toward +x (away from the robot); y under 1.00 cm either way"),
        ((0.02, 0.02, 0.0), "plus_x_plus_y",
         "x at least 1.00 cm toward +x (away from the robot); y at least 1.00 cm toward +y (robot left)"),
        ((-0.01, -0.0099, 0.0), "minus_x", "x at least 1.00 cm toward -x (toward the robot); y under 1.00 cm either way"),
        ((0.0, -0.05, 0.1), "minus_y", "x under 1.00 cm either way; y at least 1.00 cm toward -y (robot right)"),
        ((0.009, -0.009, 0.0), "none_xy", "|x| and |y| both under 1.00 cm"),
    ]
    for d, key, text in table:
        assert dir_xy_label(d) == key and text in xy["criteria"][key]
    mtable = [(0.0, "tiny", "under 0.71 cm"), (0.0071, "small", "from 0.71 cm to under 1.41 cm"),
              (0.02, "medium", "from 1.41 cm to under 2.83 cm"), (0.03, "large", "from 2.83 cm to under 5.66 cm"),
              (0.2, "xlarge", "5.66 cm or more")]
    for n, key, text in mtable:
        assert mag_label((n, 0.0, 0.0)) == key and text in mag["criteria"][key]
    # the same option keys / names (decision tokens) and order as the modular tables; the other texts are unchanged
    mod, _, _ = build_snapshot_request(_line("descend"))
    for q in ("dir_xy", "mag_coarse"):
        assert list(mod["questions"][f"ds21.{q}"]["criteria"]) == list(_fused_desc(q)["criteria"])
        assert "sub-goal" not in mod["questions"][f"ds21.{q}"]["instructions"]  # modular / stage A / E0.5 unchanged
    fus, _, _ = build_snapshot_request(_line("descend"), fused=True)
    for qid in ("ds21.dir_z", "ds21.target", "ds21.phase", "mon.progress"):
        assert fus["questions"][qid] == mod["questions"][qid]


def test_fused_text_is_byte_identical_in_training_items_and_the_runtime_request():
    from harvest.clients.jevl import question_text
    from harvest.runtime.models import FUSED_QUESTIONS, build_live_request
    from harvest.train.stagea_data import FnSource, build_items
    from harvest.train.stageb_data import QUESTIONS, image_only_state
    raw = {"grip": {"pos": [0.3, -0.1, 0.25], "w": 0.107, "effort": 0.0},
           "objs": {k: {"pos": [0.4, -0.2, 0.05], "quat": [1, 0, 0, 0], "he": [0.03, 0.03, 0.05]} for k in ("o3", "o5")},
           "contacts": [], "support": {}}
    s0 = "t_state: f3\nrobot: gripper=open"
    req, shown = build_live_request(3, "approach", s0, ["o3", "o5"], raw, state="IMG", questions=FUSED_QUESTIONS)
    ln = {"seed": 0, "kind": "P0", "k": 30, "ds_id": "ds3", "phase": "approach", "text_state": s0, "split": "fit",
          "decision": True, "images": {"cam_head": "h.jpg"}, "state": {"present": ["o3", "o5"], "obs": {"raw": raw}},
          "segment": "segment: now=unknown do=unknown next=unknown", "last_step": "none"}
    items = build_items([ln], FnSource(lambda line, q, keys: ({keys[0]}, False)), lambda x: image_only_state(s0),
                        questions=QUESTIONS)
    live = {shown[qid][0]: question_text(req["state"], qid, spec) for qid, spec in req["questions"].items()}
    assert {it["question"]: it["text"] for it in items} == live


def test_live_request_question_sets_by_backend():
    from harvest.runtime.models import DECISION_QUESTIONS, FUSED_QUESTIONS, build_live_request, decision_questions
    assert FUSED_QUESTIONS == DECISION_QUESTIONS + ("gripper",)
    assert decision_questions("fused") == FUSED_QUESTIONS and decision_questions("modular") == DECISION_QUESTIONS
    raw = {"grip": {"pos": [0.3, -0.1, 0.25], "w": 0.107, "effort": 0.0},
           "objs": {k: {"pos": [0.4, -0.2, 0.05], "quat": [1, 0, 0, 0], "he": [0.03, 0.03, 0.05]} for k in ("o3", "o5")},
           "contacts": [], "support": {}}
    req, shown = build_live_request(3, "approach", "t_state: f3\nrobot: gripper=open", ["o3", "o5"], raw, state="IMG",
                                    questions=FUSED_QUESTIONS)
    assert [q for q, _ in shown.values()] == list(FUSED_QUESTIONS) and list(req["questions"])[-1] == "ds3.gripper"
    _, shown5 = build_live_request(3, "approach", "t_state: f3\nrobot: gripper=open", ["o3", "o5"], raw)
    assert [q for q, _ in shown5.values()] == list(DECISION_QUESTIONS)


def test_question_ids_include_the_gripper_for_the_fused_set(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "qid.json"))
    from harvest.runtime.models import FUSED_QUESTIONS
    from harvest.runtime.run_r5 import question_ids
    q5, q6 = question_ids("HW", "IMG"), question_ids("HW", "IMG", questions=FUSED_QUESTIONS)
    assert "gripper" not in q5 and set(q6) == set(FUSED_QUESTIONS) and "@v" in q6["gripper"]
    # ruling PH-A1: the fused dir_xy / mag_coarse wording differs from the modular one (new ids); the rest are shared
    assert {q: q6[q] for q in q5 if q not in ("dir_xy", "mag_coarse")} == \
        {q: v for q, v in q5.items() if q not in ("dir_xy", "mag_coarse")}
    assert q6["dir_xy"] != q5["dir_xy"] and q6["mag_coarse"] != q5["mag_coarse"]


def test_stage_b_question_slots_and_decision_ids():
    from harvest.train import stageb_data as D
    assert D.QUESTIONS == ("dir_xy", "dir_z", "mag_coarse", "target", "phase", "gripper")  # appended: slots 0-4 kept
    v = D.Vocab(["gripper=close", "dir_xy=plus_x"])
    assert D.dec_ids({"gripper": "close", "dir_xy": "plus_x"}, v) == [2, 0, 0, 0, 0, 1]


def test_stage_b_items_and_committed_carry_the_gripper_label(tmp_path):
    from harvest.train import stageb_data as D
    TS = ('t_state: f13 (t=0.66s)  contract: c1  stage: S1 "pick up mug o3"\nrobot: gripper=open arm=moving\n'
          "stage S1: exit=holding(o3) lifted(o3) invariants= elapsed=normal")
    folder = tmp_path / "pool"
    folder.mkdir()
    lines, rows, v2 = [], [], []
    for k, ph in ((21, "descend"), (22, "close"), (23, "open")):
        lines.append({"seed": 2000, "kind": "P0", "split": "fit", "k": k, "ds_id": f"ds{k}", "phase": ph,
                      "decision": True, "text_state": TS, "state": {"present": ["o3", "o5"]},
                      "images": {"cam_head": f"h{k}.jpg", "cam_wrist_right": f"w{k}.jpg"}, "oracle": {}})
        H = 15
        rows.append({"seed": 2000, "kind": "P0", "k": k, "hz": 30, "H": H, "arm": "right", "skill_id": "pick",
                     "phase_id": ph, "proprio": {"q": [0.1] * 7, "qd": [0.0] * 7, "tau": [1.0] * 7,
                                                 "grip": [0.04, 0.0]},
                     "action_exec": [[0.0] * 8] * H, "action_script": [[0.0] * 8] * H, "valid": [1] * H,
                     "aux": {"reg": {}, "cls": {}}})
        v2.append({"seed": 2000, "kind": "P0", "k": k,
                   "labels_v2": {"dir_xy": "none_xy", "dir_z": "down", "mag_coarse": "small", "target": "o3",
                                 "phase_choice": "continue", "progress": None}})
    (folder / "ep2000.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    (tmp_path / "pool.labels_v2.jsonl").write_text("".join(json.dumps(x) + "\n" for x in v2))
    (tmp_path / "pool.stageb.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    ss = D.load_stageb(str(folder))
    assert [s["committed"]["gripper"] for s in ss] == ["keep", "close", "open"]
    from harvest.serialize import MOTION_UNKNOWN
    assert [s["context"]["text"].split("\n")[-2:] for s in ss] == [
        [G.segment_from_phase(ph), MOTION_UNKNOWN] for ph in ("descend", "close", "open")]
    for s in ss:  # the DecCall items carry the same state up to the (b) line
        assert all(it["text"].startswith(s["context"]["text"] + "\nlast_step: none\n\nQuestion") for it in s["items"])
    for s in ss:
        assert [it["question"] for it in s["items"]] == list(D.QUESTIONS)
        g = [it for it in s["items"] if it["question"] == "gripper"][0]
        assert g["names"] == ["close", "open", "keep", "NONE_ESCALATE"] and g["target"] == [s["committed"]["gripper"]]
    vocab = D.build_vocabs(ss)["dec"]
    assert D.dec_ids(ss[1]["committed"], vocab)[5] == vocab.get("gripper=close") > 0  # expert slot 5 (conditioning)


def test_stage_a_items_do_not_ask_the_gripper():
    from harvest.train.stagea_data import FnSource, build_items
    ln = {**_line("close"), "split": "fit", "decision": True, "images": {"cam_head": "h.jpg"}}
    items = build_items([ln], FnSource(lambda line, q, keys: ({keys[0]}, False)))
    assert "gripper" not in {it["question"] for it in items} and len(items) == 5


def test_se2e_gripper_label_from_the_recorded_command():
    from harvest.train import se2e_data as S
    # RB1: joint value 0 = open, 1.10 = closed (stageb_data.GRIP_CAL); label window = label_steps (3) at 10 Hz
    def row(g0, g3):
        a = [[0.0] * 7 + [g0]] + [[0.0] * 7 + [g0]] * 2 + [[0.0] * 7 + [g3]] + [[0.0] * 7 + [g3]]
        return {"kind": "RB1", "fps_src": 10, "action_exec": a, "label_steps": 3, "label_window_s": 0.3}
    assert S.gripper_label(row(0.0, 1.10)) == "close"  # command closes fully within 0.3 s
    assert S.gripper_label(row(1.10, 0.0)) == "open"
    assert S.gripper_label(row(0.5, 0.5)) == "keep"
    # boundary: |d openness| / 0.3 s at the 0.176 /s threshold -> keep; just above -> close
    d = 0.176 * 0.3 * 1.10
    assert S.gripper_label(row(0.2, 0.2 + d * 0.999)) == "keep"
    assert S.gripper_label(row(0.2, 0.2 + d * 1.001)) == "close"
    with pytest.raises(ValueError, match="label_steps"):
        S.gripper_label({**row(0.0, 1.1), "label_steps": 5})
    assert S.gripper_label({k: v for k, v in row(0.0, 1.1).items() if k != "label_steps"}) is None  # not derivable
