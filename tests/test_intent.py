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
    from harvest.serialize import (LINE_SEGMENTS, SEGMENT_ACTIONS, SEGMENT_UNKNOWN, SEGMENTS, check_segment,
                                   segment_line)
    # fix round 1 (controller ruling F12): a segment CONTAINS its gripper event (no grasp / release segment names)
    assert LINE_SEGMENTS == ("approach", "carry", "retreat", "done") and SEGMENT_ACTIONS == ("close", "open", "none")
    # Astra's plan names (E-ACC v2 answer vocabulary) map onto the line segment that contains them
    assert set(G.PLAN_TO_LINE) == set(SEGMENTS) and set(G.PLAN_TO_LINE.values()) == set(LINE_SEGMENTS)
    assert {G.PLAN_TO_LINE[s] for s in ("descend", "grasp")} == {"approach"}
    assert {G.PLAN_TO_LINE[s] for s in ("lift", "place", "release")} == {"carry"}
    assert segment_line("approach", "close", "carry") == "segment: now=approach do=close next=carry"
    assert check_segment(SEGMENT_UNKNOWN) == SEGMENT_UNKNOWN
    for bad in (("reach", "none", "carry"), ("approach", "keep", "carry"), ("approach", "none", "o3"),
                ("grasp", "close", "carry"), ("approach", "close", "lift")):
        with pytest.raises(ValueError, match="segment value"):
            segment_line(*bad)
    for bad in ("segment: now=approach do=none", "segment now=approach do=none next=carry",
                "segment: now=approach do=none next=carry x=1"):
        with pytest.raises(ValueError, match="segment"):
            check_segment(bad)


def test_segment_rule_from_the_r2_phase_sequence():
    # the pick segment holds approach + descend + close (do=close), the place segment lift .. open (do=open)
    pick, carry = "now=approach do=close next=carry", "now=carry do=open next=retreat"
    want = {"approach": pick, "descend": pick, "close": pick, "lift": carry, "carry": carry, "place_descend": carry,
            "open": carry, "retreat": "now=retreat do=none next=done", "done": "now=done do=none next=done"}
    from harvest.sim.snapshot import PHASE_ORDER
    assert set(want) == set(PHASE_ORDER) == set(G.PHASE_SEGMENT)  # every planner phase has a segment
    for ph, s in want.items():
        assert G.segment_from_phase(ph) == "segment: " + s
    assert G.segment_from_phase("na") == G.segment_from_phase(None) == "segment: now=unknown do=unknown next=unknown"


def test_segment_rule_from_s_e2e_gripper_events():
    labs = ["keep", "keep", "close", "close", "keep", "keep", "open", "keep", "close", "keep", "open", "keep"]
    got = [s[len("segment: "):] for s in G.segments_from_events(labs)]
    A2, C2 = "now=approach do=close next=carry", "now=carry do=open next=approach"
    C3, R = "now=carry do=open next=retreat", "now=retreat do=none next=done"
    assert got == [A2, A2, A2, A2, C2, C2, C2, A2, A2, C3, C3, R]
    assert G.segments_from_events(["keep", "keep"]) == ["segment: now=unknown do=unknown next=unknown"] * 2
    # holding at the end without a release ahead: carry, nothing planned
    assert G.segments_from_events(["close", "keep"])[1] == "segment: now=carry do=none next=unknown"
    # starting while holding: the first event is a release
    assert G.segments_from_events(["keep", "open", "keep"]) == ["segment: " + C3, "segment: " + C3, "segment: " + R]
    assert G.segments_from_events([]) == []
    got = G.segments_from_events(["keep", None, "close"])  # None = not derivable: unknown, and no event
    assert got[0] == "segment: " + A2 and got[1] == G.SEGMENT_UNKNOWN and got[2] == "segment: " + A2


def _r2_phase_sequence():
    # a planned R2 episode sampled several times per phase (the snapshot rows of one episode)
    return [ph for ph, n in (("approach", 4), ("descend", 3), ("close", 2), ("lift", 2), ("carry", 3),
                             ("place_descend", 3), ("open", 2), ("retreat", 2), ("done", 1)) for _ in range(n)]


def test_the_segment_line_does_not_give_away_the_gripper_label():
    """canon §90: Astra names the segment and its action, the VLA decides WHEN -- so the gripper label must not be a
    function of the segment line: every segment whose action is close / open also holds keep rows (the event inside
    is that action), and the segment line never changes where a gripper event starts."""
    ph = _r2_phase_sequence()
    r2 = ([G.segment_from_phase(p) for p in ph], [G.from_phase(p) for p in ph])
    ev = ["keep", "keep", "keep", "close", "close", "keep", "keep", "keep", "open", "open", "keep", "keep"]
    for segs, labels in (r2, (G.segments_from_events(ev), ev)):
        by = {}
        for s, g in zip(segs, labels):
            by.setdefault(s, set()).add(g)
        assert any(len(v) > 1 for v in by.values())  # the label is not a function of the segment line
        for s, v in by.items():
            if v & {"close", "open"}:
                assert "keep" in v, (s, v)
                assert v - {"keep"} == {s.split(" do=")[1].split(" ")[0]}, (s, v)
        for i in range(1, len(labels)):
            if labels[i] in ("close", "open") and labels[i - 1] == "keep":
                assert segs[i] == segs[i - 1]


def test_deccall_state_tail_order_segment_motion_last_step():
    req, _, _ = build_snapshot_request(_line("close"))
    assert req["state"].split("\n")[-3:] == ["segment: now=approach do=close next=carry",
                                             "motion: arm=unknown gripper=unknown", "last_step: none"]
    seg = "segment: now=carry do=open next=retreat"  # an explicit line (runtime: Astra's plan) wins over the rule
    req, _, _ = build_snapshot_request({**_line("close"), "segment": seg})
    assert req["state"].split("\n")[-3] == seg
    with pytest.raises(ValueError, match="segment"):
        build_snapshot_request({**_line("close"), "segment": "segment: now=grasp do=close next=carry"})


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
        return {"kind": "RB1", "fps_src": 10, "hz": 10, "action_exec": a, "label_steps": 3, "label_window_s": 0.3}
    assert S.gripper_label(row(0.0, 1.10)) == "close"  # command closes fully within 0.3 s
    assert S.gripper_label(row(1.10, 0.0)) == "open"
    assert S.gripper_label(row(0.5, 0.5)) == "keep"
    # boundary: |d openness| / 0.3 s at the 0.176 /s threshold -> keep; just above -> close
    d = 0.176 * 0.3 * 1.10
    assert S.gripper_label(row(0.2, 0.2 + d * 0.999)) == "keep"
    assert S.gripper_label(row(0.2, 0.2 + d * 1.001)) == "close"
    assert S.gripper_label({k: v for k, v in row(0.0, 1.1).items() if k != "label_steps"}) is None  # not derivable


def test_se2e_gripper_label_indexes_the_chunk_in_its_own_rate():
    """Fix round 1 item 9: action_exec is resampled at the row's hz, the label window is in seconds -- the chunk index
    is window * hz (not the source-fps label_steps); a window that is no whole number of chunk steps is refused."""
    from harvest.train import se2e_data as S
    g = [0.0, 0.0, 0.0, 0.0, 1.1, 1.1]  # the command closes between chunk steps 3 and 4 (hz 10)
    a = [[0.0] * 7 + [x] for x in g]
    # source 20 fps -> label_steps 6 source frames = 0.3 s = 3 chunk steps at hz 10: the command has not closed yet
    r = {"kind": "RB1", "fps_src": 20, "hz": 10, "action_exec": a, "label_steps": 6, "label_window_s": 0.3}
    assert S.gripper_label(r) == "keep"  # indexing a[6] (source steps) would have raised / read the wrong time
    assert S.gripper_label({**r, "label_window_s": 0.4}) == "close"
    with pytest.raises(ValueError, match="whole number"):
        S.gripper_label({**r, "label_window_s": 1.0 / 3.0, "label_steps": 10, "fps_src": 30})
    with pytest.raises(ValueError, match="chunk"):
        S.gripper_label({**r, "label_window_s": 0.6})


def test_se2e_segment_lines_see_an_event_between_stride_sampled_rows():
    """Fix round 1 item 9: rows sampled every 5 frames with a 3-frame label window -- a grasp between two rows is in
    no row's window; segment_lines finds it from the commands of consecutive rows (same rate rule) so the segments
    around it are approach / carry, while the rows' own gripper labels stay keep."""
    from harvest.train import se2e_data as S

    def row(k, g0):
        a = [[0.0] * 7 + [g0]] * 5
        return {"kind": "RB1", "seed": 7, "k": k, "fps_src": 10, "hz": 10, "action_exec": a, "label_steps": 3,
                "label_window_s": 0.3}
    rows = [row(0, 0.0), row(5, 0.0), row(10, 1.1), row(15, 1.1)]  # closed between frame 8 and 10
    assert [S.gripper_label(r) for r in rows] == ["keep"] * 4
    segs = S.segment_lines(rows)
    assert [segs[f"RB1_ep7_k{k}"] for k in (0, 5, 10, 15)] == [
        "segment: now=approach do=close next=carry"] * 2 + ["segment: now=carry do=none next=unknown"] * 2


def test_segment_dropout_training_share():
    """Fix round 1 item 2: the runtime shows the unknown segment line (until Astra's plan, VLA-alone arms, the
    modular stack) -- training replaces the line by unknown with p = SEGMENT_DROPOUT (= the §83 motion line's 0.3),
    per snapshot key and step, all items of a snapshot together, and composes with the motion-line dropout."""
    from harvest.serialize import MOTION_UNKNOWN, SEGMENT_UNKNOWN
    assert G.SEGMENT_DROPOUT == 0.3
    seg = "segment: now=approach do=close next=carry"
    ctx = f"task: x\n{seg}\nmotion: arm=slow gripper=still"
    assert G.drop_segment(ctx) == f"task: x\n{SEGMENT_UNKNOWN}\nmotion: arm=slow gripper=still"
    assert G.drop_segment("no line") == "no line"
    n = 20000
    share = sum(G.segment_dropped(f"k{i}", 3, 0) for i in range(n)) / n
    assert abs(share - 0.3) < 0.015
    assert not any(G.segment_dropped(f"k{i}", 3, 0, p=0.0) for i in range(100))
    assert [G.segment_dropped("k1", s, 0) for s in range(50)] == [G.segment_dropped("k1", s, 0) for s in range(50)]
    assert len({tuple(G.segment_dropped(f"k{i}", s, 0) for i in range(40)) for s in range(5)}) > 1  # varies by step
    sample = {"key": "k1", "context": {"text": ctx}, "items": [{"text": ctx + "\nlast_step: none\n\nQuestion a"},
                                                               {"text": ctx + "\nlast_step: none\n\nQuestion b"}]}
    batch = [dict(sample, key=f"k{i}") for i in range(200)]
    out = G.segment_dropout(batch, 5, 1)
    dropped = [s for s in out if SEGMENT_UNKNOWN in s["context"]["text"]]
    assert 30 < len(dropped) < 90
    for s in dropped:
        assert all(SEGMENT_UNKNOWN in it["text"] and seg not in it["text"] for it in s["items"])
        assert G.segment_dropped(s["key"], 5, 1)
    assert batch[0]["context"]["text"] == ctx  # inputs not modified
    items = [{"key": "a", "text": ctx + "\nQ1"}, {"key": "a", "text": ctx + "\nQ2"}, {"key": "b", "text": ctx}]
    for step in range(20):  # stage A: the items of one snapshot drop together (shared prefix)
        got = G.segment_dropout_items(items, step, 0)
        assert (SEGMENT_UNKNOWN in got[0]["text"]) == (SEGMENT_UNKNOWN in got[1]["text"])
    # composes with the motion-line dropout (both lines unknown when both fire)
    mot = lambda b, step: [{**s, "context": {"text": s["context"]["text"].replace(  # noqa: E731
        "motion: arm=slow gripper=still", MOTION_UNKNOWN)}, "items": s["items"]} for s in b]
    f = G.with_segment_dropout(mot, 0.3, 1)
    both = [s for s in f(batch, 5) if SEGMENT_UNKNOWN in s["context"]["text"]]
    assert both and all(MOTION_UNKNOWN in s["context"]["text"] for s in both)
    assert G.with_segment_dropout(None, 0.0, 1) is None and G.with_segment_dropout(mot, 0.0, 1) is mot
