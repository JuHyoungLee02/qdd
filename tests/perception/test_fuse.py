import numpy as np

from harvest.perception.fuse import CamDet, Tracker, fuse


def _d(cam, p, depth, n=100, score=0.9, second=None):
    return CamDet(cam=cam, score=score, n_valid=n, point=np.asarray(p, float), depth_med=depth, second=second)


def test_prefers_wrist_inside_its_range():
    f = fuse(_d("cam_head", [0.40, 0, 0.05], 0.8), _d("cam_wrist_right", [0.41, 0, 0.05], 0.25))
    assert f["source"] == "wrist" and np.allclose(f["pos"], [0.41, 0, 0.05])
    assert f["seen"] == ["cam_head", "cam_wrist_right"] and not f["id_uncertain"]


def test_head_when_wrist_out_of_range_or_missing():
    f = fuse(_d("cam_head", [0.40, 0, 0.05], 0.8), _d("cam_wrist_right", [0.41, 0, 0.05], 0.60))
    assert f["source"] == "head"
    f = fuse(_d("cam_head", [0.40, 0, 0.05], 0.8), None)
    assert f["source"] == "head" and f["seen"] == ["cam_head"]
    f = fuse(_d("cam_head", [0.40, 0, 0.05], 0.8), _d("cam_wrist_right", [0.41, 0, 0.05], 0.05))  # too close
    assert f["source"] == "head"


def test_wrist_out_of_range_only_as_last_resort():
    f = fuse(None, _d("cam_wrist_right", [0.41, 0, 0.05], 0.60))
    assert f["source"] == "wrist_oor"


def test_too_few_depth_pixels_is_not_a_detection():
    f = fuse(_d("cam_head", [0.40, 0, 0.05], 0.8, n=5), None)
    assert f["pos"] is None and f["source"] is None and f["seen"] == []


def test_id_uncertain_from_runner_up_or_camera_disagreement():
    f = fuse(_d("cam_head", [0.40, 0, 0.05], 0.8, second=(0.7, np.array([0.55, 0.1, 0.05]))), None)
    assert f["id_uncertain"]
    f = fuse(_d("cam_head", [0.40, 0, 0.05], 0.8, second=(0.3, np.array([0.55, 0.1, 0.05]))), None)
    assert not f["id_uncertain"]  # weak runner-up
    f = fuse(_d("cam_head", [0.40, 0, 0.05], 0.8, second=(0.7, np.array([0.41, 0.0, 0.05]))), None)
    assert not f["id_uncertain"]  # same object split in two masks
    f = fuse(_d("cam_head", [0.20, 0, 0.05], 0.8), _d("cam_wrist_right", [0.41, 0, 0.05], 0.25))
    assert f["id_uncertain"] and f["source"] == "wrist"


def test_tracker_holds_last_estimate_and_flags_occlusion():
    tr = Tracker()
    a = tr.update("o3", fuse(_d("cam_head", [0.4, 0, 0.05], 0.8), None))
    assert not a["occluded"] and np.allclose(a["pos"], [0.4, 0, 0.05])
    b = tr.update("o3", fuse(None, None))
    assert b["occluded"] and np.allclose(b["pos"], [0.4, 0, 0.05]) and b["held_frames"] == 1
    c = tr.update("o5", fuse(None, None))
    assert c["occluded"] and c["pos"] is None
