import json

import pytest

from harvest.astra_solo import pt_prompts as PT
from harvest.astra_solo import pt_schema as PS
from harvest.l9 import hand as H
from harvest.teach_pt import collect as C
from harvest.teach_pt import min_format as MF

from astra_solo.test_pt_episode import PadWorld

PT_ANS = {"assessment": {"task_progress": {"verified_completed": [], "currently_attempting": "x", "remaining": []},
                         "execution_status": "progressing", "evidence": "e", "evidence_view": "both",
                         "confidence": "high"},
          "command": {"mode": "point", "point_2d": [500, 400], "height": "grasp", "gripper": "close"}, "reason": "r"}


def test_parser_without_hand_unchanged():
    out, err = PS.validate(json.dumps(PT_ANS))
    assert not err and "hand" not in out["command"]


def test_parser_hand_left_and_bad():
    a = json.loads(json.dumps(PT_ANS))
    a["command"]["hand"] = "left"
    out, err = PS.validate(json.dumps(a))
    assert not err and out["command"]["hand"] == "left"
    a["command"]["hand"] = "up"
    out, err = PS.validate(json.dumps(a))
    assert out is None and any("hand" in e for e in err)


def test_left_text_swaps_only_arm_words():
    t = PT.STATIC
    assert "RIGHT wrist camera" in t
    lt = H.left_text(t)
    assert "RIGHT wrist camera" not in lt and "LEFT wrist camera" in lt and "right hand" not in lt
    assert H.left_text(lt.replace("LEFT", "RIGHT").replace("left hand", "right hand")) .count("LEFT wrist") >= 1
    assert len(lt.split()) == len(t.split())  # word count unchanged
    assert "(the robot's left)" == H.left_text("(the robot's left)")


def test_hand_format_and_answer():
    f = H.add_hand_format(PT.ANSWER)
    assert H.HAND_FIELD in f and H.add_hand_format(f) == f
    a = json.loads(H.with_hand(json.dumps(PT_ANS), "left"))
    assert a["command"]["hand"] == "left"
    g = dict(PT_ANS, command={"mode": "gripper", "gripper": "open"})
    assert "hand" not in json.loads(H.with_hand(json.dumps(g), "left"))["command"]
    assert H.with_hand(None, "left") is None
    assert H.hand_of({}) == "right"


@pytest.fixture(scope="module")
def ep(tmp_path_factory):
    root = tmp_path_factory.mktemp("hand")
    C.collect_episode(PadWorld(), 20100, "mug_tray", "standard", str(root / "train" / "standard" / "mug_tray_s20100"),
                      p=0.35)
    from harvest.teach_pt import dataset as DS
    rows = DS.load_rows(str(root / "train" / "standard" / "mug_tray_s20100"), "train")
    return root, [r for r in rows if r.get("pt_answer") is not None]


def test_min_row_l8s_unchanged_and_left(ep):
    root, rows = ep
    r = rows[0]
    a = MF.row(r, str(root / "o1"), "d-min")
    b = MF.row(dict(r, hand=None), str(root / "o2"), "d-min")
    assert open(a["prompt_path"], encoding="utf-8").read() == open(b["prompt_path"], encoding="utf-8").read()
    assert a["answer"] == b["answer"] == r["pt_answer"]
    c = MF.row(dict(r, hand="left"), str(root / "o3"), "d-min")
    txt = open(c["prompt_path"], encoding="utf-8").read()
    assert "LEFT wrist camera" in txt and "RIGHT wrist camera" not in txt and H.HAND_FIELD in txt
    assert json.loads(c["answer"])["command"].get("hand", "left") == "left"
    ok, err = PS.validate(c["answer"])
    assert not err
    d = MF.row(dict(r, hand="right"), str(root / "o4"), "d-min")
    assert "RIGHT wrist camera" in open(d["prompt_path"], encoding="utf-8").read()
