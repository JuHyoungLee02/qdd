import numpy as np

from harvest.couple.overlay import INSET, CamModel, EETrace, draw_overlay, polylines, project, uv255

R = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])  # optical x = -Y, y = -Z, z = +X (Isaac world)
CAM = CamModel.from_dict({"K": [[100, 0, 80], [0, 100, 60], [0, 0, 1]], "R": R.tolist(), "t": [0, 0, 0],
                          "W": 160, "H": 120})


def test_projection_center_and_right():
    u, v, z = project(CAM, [1.0, 0.0, 0.0])
    assert (round(u, 6), round(v, 6), round(z, 6)) == (80.0, 60.0, 1.0)
    u2, _, _ = project(CAM, [1.0, -0.1, 0.0])
    assert u2 > 80.0  # world -y is image right
    assert uv255(CAM, [1.0, 0.0, 0.0]) == [128, 128] and uv255(CAM, [-1.0, 0.0, 0.0]) is None


def test_head_overlay_draws_around_the_tip_only():
    img = np.zeros((120, 160, 3), np.uint8)
    tip = np.array([1.0, 0.0, 0.0])
    out = draw_overlay(img, CAM, tip=tip, trace=[tip + [0, 0.05, 0], tip], next_vec=np.array([0, -0.02, 0]),
                       offset_vec=np.array([0, 0, 0.02]), wrist=False)
    assert out.shape == img.shape and out[53:68, 72:89].any()  # ring / axes / arrows around the tip (80, 60)
    assert not out[:20, :20].any() and not out[100:, 140:].any()  # far corners untouched
    assert img.sum() == 0  # the input frame is not modified


def test_wrist_overlay_stays_inside_the_corner_box():
    img = np.zeros((120, 160, 3), np.uint8)
    out = draw_overlay(img, CAM, tip=np.array([1.0, 0, 0]), trace=[], next_vec=np.array([0, -0.02, 0]),
                       offset_vec=None, wrist=True)
    ys, xs = np.nonzero(out.sum(axis=2))
    assert len(xs) > 0 and xs.min() >= 160 - INSET - 3 and ys.max() <= INSET + 3


def test_polylines_skip_cameras_without_model():
    tr = EETrace(keep_s=5.0)
    for i in range(30):
        tr.add(i * 0.1, [1.0, -0.01 * i, 0.0])
    pts = [p for _, p in tr.window(2.9, 2.5)]
    out = polylines({"cam_head": CAM}, pts[::-1])
    assert list(out) == ["cam_head"] and 1 <= len(out["cam_head"]) <= 5
    assert out["cam_head"][0] == uv255(CAM, pts[-1])  # current point first (MolmoAct p1)
    assert polylines({}, pts[::-1]) == {} and polylines({"cam_head": CAM}, []) == {}
