"""r2-cams (user 10-03 02h): each robot's own cameras, any number -- 4 standard slots first, extra native views
tagged after them; one tag function (views9.view_label / view_line) for builder, trainer and runtime; the gate."""
import json
import os

import numpy as np
import pytest

from harvest.l9 import specgate9 as SG
from harvest.l9 import views9 as V
from harvest.teach_l8.dataset import image_labels

FX = os.path.join(os.path.dirname(__file__), "fixtures")
CAM = {"W": 424, "H": 240, "fx": 200.0, "fy": 200.0, "cx": 212.0, "cy": 120.0,
       "R": [[0, -1, 0], [-1, 0, 0], [0, 0, -1.0]], "t": [0.3, 0.2, 1.2]}
ANS = json.dumps({"assessment": {"evidence_view": "both"}, "command": {"mode": "point", "point_2d": [500, 500]}})


def _text():
    return open(os.path.join(FX, "l9_v2_1.txt"), encoding="utf-8").read()


def _row(res, robot):
    return {"robot": robot, "images": res["images"], "image_views": res["image_views"], "spec_version": SG.SPEC_CAMS}


def _one(robot, used, other, extras=(), third=None):
    return V.canonical(_text(), ANS, "right", "h.png", used, other, third, np.random.default_rng(0), wrist_keep=1.0,
                       robot=robot, extras=extras)


def test_one_camera_robot_g1_drops_palm_views():
    r = _one("g1", ("w.png", CAM), ("o.png", CAM))
    assert r["images"] == ["h.png"] and r["image_views"] == ["head"]
    assert V.parse_slots(r["text"]) == {"head": 1, "wrist_left": None, "wrist_right": None, "third_person": None}
    assert "wrist camera (image" not in r["text"]
    assert SG.view_schema_errors(_row(r, "g1"), r["text"]) == []


def test_two_camera_robot_franka():
    r = _one("franka_mast", ("w.png", CAM), None)
    assert r["image_views"] == ["head", "wrist_right"]
    assert SG.view_schema_errors(_row(r, "franka_mast"), r["text"]) == []


def test_five_camera_robot_extras_after_slots():
    ex = [("head_right", "hr.png", CAM), ("chest", "c.png", CAM)]
    r = _one("r1pro", ("w.png", CAM), ("o.png", CAM), ex)
    assert r["image_views"] == ["head", "wrist_left", "wrist_right", "head_right", "chest"]
    assert r["images"] == ["h.png", "o.png", "w.png", "hr.png", "c.png"]
    got = V.parse_slots(r["text"])
    assert list(got) == ["head", "wrist_left", "wrist_right", "third_person", "head_right", "chest"]
    assert got["third_person"] is None and got["head_right"] == 4 and got["chest"] == 5
    lines = [ln for ln in r["text"].split("\n") if ln.startswith("- view:")]
    assert lines[3] == "- view: third_person (none)" and lines[4].startswith("- view: head_right -- Image 4: right eye")
    assert SG.view_schema_errors(_row(r, "r1pro"), r["text"]) == []
    assert image_labels(5, r["image_views"])[3:] == ["right head camera", "chest camera"]


def test_extras_with_third_person_keep_slot_order():
    r = _one("ffw_sg2", ("w.png", CAM), ("o.png", CAM), [("head_right", "hr.png", CAM)], third=("t.png", CAM))
    assert r["image_views"] == ["head", "wrist_left", "wrist_right", "third_person", "head_right"]
    assert SG.view_schema_errors(_row(r, "ffw_sg2"), r["text"]) == []


def test_no_extras_is_byte_identical_to_pre_r2():
    a = V.canonical(_text(), ANS, "right", "h.png", ("w.png", CAM), ("o.png", CAM), None, V.row_rng("x"))
    b = V.canonical(_text(), ANS, "right", "h.png", ("w.png", CAM), ("o.png", CAM), None, V.row_rng("x"),
                    robot="ffw_sg2", extras=())
    assert a == b


def test_unknown_extra_view_rejected():
    with pytest.raises(ValueError):
        _one("r1pro", None, None, [("nose_cam", "n.png", CAM)])


def test_gate_catches_bad_rows():
    r = _one("ffw_sg2", ("w.png", CAM), ("o.png", CAM), [("chest", "c.png", CAM)])
    ok = _row(r, "ffw_sg2")
    assert SG.view_schema_errors(dict(ok, images=r["images"][:-1]), r["text"])  # image count
    assert SG.view_schema_errors(dict(ok, image_views=r["image_views"][::-1]), r["text"])  # order
    assert SG.view_schema_errors(dict(ok, spec_version=SG.SPEC), r["text"])  # old spec tag
    assert SG.view_schema_errors(dict(ok, robot="g1"), r["text"])  # G1 with wrist views
    bad = r["text"].replace("- view: chest --", "- view: nose_cam --")
    assert SG.view_schema_errors(ok, bad)  # unknown extra name
    swapped = r["text"].replace("- view: wrist_left", "- view: TMP").replace("- view: wrist_right", "- view: wrist_left") \
        .replace("- view: TMP", "- view: wrist_right")
    assert SG.view_schema_errors(ok, swapped)  # slot order


def test_gates_views_flag():
    r = _one("r1pro", ("w.png", CAM), None, [("head_right", "hr.png", CAM)])
    row = dict(_row(r, "r1pro"), id="a", prompt_path="p", answer=r["answer"])
    g = SG.gates([row], {"p": r["text"]}, views=True)
    assert g["view_schema_errors"] == 0 and g["ok"], g
    g = SG.gates([dict(row, spec_version=SG.SPEC)], {"p": r["text"]}, views=True)
    assert g["view_schema_errors"] == 1 and not g["ok"]
    assert SG.spec_family(SG.SPEC_CAMS) == SG.SPEC


def test_build_extra_views_from_cams_json(tmp_path):
    from harvest.l9 import build9 as B9
    d = tmp_path / "call"
    d.mkdir()
    (d / "img_chest.png").write_bytes(b"x")
    cams = {"head": CAM, "extra_views": {"chest": dict(CAM, img="img_chest.png"),
                                         "head_right": dict(CAM, img="missing.png")}}
    (d / "cams.json").write_text(json.dumps(cams))
    ex = B9.extra_views({"cams_path": str(d / "cams.json"), "call_dir": str(d)})
    assert [e[0] for e in ex] == ["chest"] and "img" not in ex[0][2]
    (d / "cams.json").write_text(json.dumps({"head": CAM}))
    assert B9.extra_views({"cams_path": str(d / "cams.json"), "call_dir": str(d)}) == []
