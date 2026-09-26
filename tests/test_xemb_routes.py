"""tools/xemb/routes.py + fmt camera-unknown: which sample types a public source may produce, by data condition
(no frame / joints only / calibrated / + depth or GT poses), and the text of an uncalibrated robot."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from xemb import fmt as F  # noqa: E402
from xemb import routes as RT  # noqa: E402


def test_no_frame_gives_pixel_only():
    s = RT.allowed(RT.Cond())
    assert s == {"ee_point_detected", "ee_trace_detected", "obj_point_detected", "format_qa"}
    assert not any(k.endswith("_cam") or k.startswith("control") for k in s)


def test_joints_only_adds_control_with_unknown_camera_and_selfcal():
    s = RT.allowed(RT.Cond(fk=True))
    assert "control_camera_unknown" in s and "selfcal" in s
    assert "ee_point_projected" not in s  # needs a calibration (shipped or self-made)
    s2 = RT.allowed(RT.Cond(fk=True, selfcal_ok=True))
    assert {"ee_point_projected", "ee_trace_projected", "control_with_camera"} <= s2


def test_metric_3d_needs_depth_or_gt_pose():
    assert "obj_center_cam" not in RT.allowed(RT.Cond(fk=True, calib=True))
    assert "obj_center_cam" in RT.allowed(RT.Cond(fk=True, calib=True, gt_pose=True))
    assert "table_plane_cam" in RT.allowed(RT.Cond(calib=True, depth=True))
    assert "obj_center_cam_pseudo" in RT.allowed(RT.Cond(calib=True, pseudo_depth_ok=True))


def test_camera_unknown_self_info_text():
    robot = {"name": "ffw_bg2", "source": "robotis/ffw_bg2_rb2", "arm": "right", "desc": "ROBOTIS AI Worker FFW-BG2",
             "gripper": {"open_gap_m": 0.1}, "workspace": {"x": [0.3, 0.6], "y": [-0.4, 0.4], "z": [-0.4, 0.0]},
             "cameras": [{"name": "head camera", "W": 672, "H": 376, "K": None, "T_base_cam": None}]}
    t = F.self_info(robot)
    assert "camera: unknown" in t
    assert "fx" not in t


def test_pixel_trace_record():
    src = {"source": "robotis/ffw_bg2_rb2", "cameras": [{"name": "head camera", "W": 672, "H": 376, "K": None}]}
    r = F.qa_trace(src, [[10.2, 20.7], [30, 40], [50, 60]], cam=0, image="a.jpg", rid="t", arm="right")
    assert r["prompt"].splitlines()[1] == "frame: pixel"
    assert json.loads(r["answer"]) == {"trace": [[10, 21], [30, 40], [50, 60]]}
    assert "camera: unknown" in r["prompt"]
