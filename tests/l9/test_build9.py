"""L9 -> d-min build: (1) L9 object lines, (2) robot profiles (gripper / cameras / request wording),
(3) the L8S build output is unchanged (golden d-min texts made with the code before the L9 changes, e9fd82c),
plus the per-row robot / camera checks."""
import glob
import json
import os

import numpy as np
import pytest

from harvest.l9 import build9 as B9
from harvest.l9 import hcam9 as HC
from harvest.l9 import robot9 as R9
from harvest.teach_pt import min_format as MF

FX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(n):
    return open(os.path.join(FX, n), encoding="utf-8").read()


# ---------------------------------------------------------------- (3) L8S unchanged
@pytest.mark.parametrize("i", [1, 2, 3])
def test_l8s_dmin_text_unchanged(i):
    assert MF.d_text(_read(f"l8s_v2_{i}.txt")) == _read(f"l8s_dmin_{i}.txt")


# ---------------------------------------------------------------- (1) L9 object lines
@pytest.mark.parametrize("n", ["l9_v2_1.txt", "l9_v2_2.txt"])
def test_l9_object_lines_strip_to_name_and_role(n):
    v2 = _read(n)
    names = B9.object_names(v2)
    assert names and all(":" not in x for x in names)
    d = MF.d_text(v2)
    block = d.split("OBJECTS (", 1)[1].split("\n", 1)[1].split("\n\n", 1)[0].split("\n")
    obj = [ln for ln in block if ln.startswith("- ")]
    assert [ln[2:].split(" (", 1)[0] for ln in obj] == names  # "- name (role)": descriptions / sizes removed
    assert not any(" cm" in ln for ln in obj)


def test_object_names_parse():
    t = "x\nOBJECTS (name: shape; ...)\n- red box: a box (the object to move)\n- block: a block of the furniture (where to put it)\n- apple: object about 7 x 7 cm, 8 cm high (obstacle)\n\nNOW"
    assert B9.object_names(t) == ["red box", "block", "apple"]


# ---------------------------------------------------------------- (2) robot profiles
def test_profiles_gripper_and_cameras():
    from harvest.sim import scene as SC
    assert SC.GRIP_MAX_W == pytest.approx(0.107) and R9.GRIP_MAX_W == pytest.approx(0.08)
    rc = SC.load_realcam()
    assert rc.CAMERA_SPECS["cam_head"]["fx"] == pytest.approx(367.0, abs=0.5)  # AI Worker ZED Mini 85 deg
    assert HC.fx_from_hfov(R9.CAM_SPECS["cam_head"]["hfov"]) == pytest.approx(489.0, abs=0.5)  # Franka mast D435
    for s in (rc.CAMERA_SPECS["cam_wrist_right"], R9.CAM_SPECS["cam_wrist_right"]):
        assert (s["width"], s["height"]) == (424, 240)
    assert R9.CAM_SPECS["cam_head"]["parent"] == "panda_link0" and R9.CAM_SPECS["cam_wrist_right"]["parent"] == "panda_hand"


def test_franka_request_wording_survives_dmin():
    v2 = R9.swap_text(_read("l9_v2_1.txt"), "franka_mast")
    d = MF.d_text(v2)
    assert "Franka Emika Panda" in d and "AI Worker" not in d and "Fully open pad gap 8.0 cm" in d
    assert "mast on the robot's stand" in d


# ---------------------------------------------------------------- camera line + row checks
def _cam_json(path, pitch=45.0, z=1.34):
    R = HC.look_R(pitch, 0.0) @ np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
    json.dump({"head": {"name": "head", "W": 672, "H": 376, "fx": 367.0, "fy": 367.0, "cx": 336.0, "cy": 188.0,
                        "R": R.tolist(), "t": [0.05, 0.0, z]}}, open(path, "w"))


def test_camera_line_position():
    t = MF.d_text(_read("l9_v2_1.txt"))
    out = B9.add_camera_line(t, "camera: head, x")
    lines = out.split("\n")
    i = lines.index(B9.CAM_ANCHOR.strip())
    assert lines[i + 1] == "- camera: head, x" and lines[i + 2].startswith("- Image 1:")
    assert B9.add_camera_line(out, "camera: head, x") == out


@pytest.mark.parametrize("robot", ["ffw_sg2", "franka_mast"])
def test_check_rows(tmp_path, robot):
    ep = tmp_path / "ep"
    call = ep / "calls" / "c000"
    os.makedirs(call)
    json.dump({"robot": robot, "arm": "right"}, open(ep / "meta.json", "w"))
    _cam_json(call / "cams.json")
    for f in ("img1_head_ring.png", "img2_right_wrist_camera.png"):
        open(call / f, "wb").write(b"x")
    v2 = _read("l9_v2_1.txt") if robot == "ffw_sg2" else R9.swap_text(_read("l9_v2_1.txt"), "franka_mast")
    line = B9.camera_of({"cams_path": str(call / "cams.json")}, robot)
    prompt = tmp_path / "p.txt"
    prompt.write_text(B9.add_camera_line(MF.d_text(v2), line), encoding="utf-8")
    row = {"kind": "control", "gen": "l9", "id": "x", "robot": robot, "camera": line, "call_dir": str(call),
           "cams_path": str(call / "cams.json"), "prompt_path": str(prompt), "label_missing": False,
           "answer": json.dumps({"command": {"mode": "point", "hand": "right"}}),
           "images": [str(call / "img1_head_ring.png"), str(call / "img2_right_wrist_camera.png")]}
    ok = B9.check_rows([row], camera_line=True)
    assert ok["n"] == 1 and ok["n_errors"] == 0, ok
    other = "franka_mast" if robot == "ffw_sg2" else "ffw_sg2"
    bad = B9.check_rows([dict(row, robot=other, answer=json.dumps({"command": {"hand": "left"}}))], camera_line=False)
    errs = bad["errors"][0]["errors"]
    assert any("robot" in e for e in errs) and any("hand" in e for e in errs) and any("camera line present" in e for e in errs)
