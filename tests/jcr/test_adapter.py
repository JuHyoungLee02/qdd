import numpy as np

from harvest.astra_motion.geometry import Cam
from harvest.jcr import adapter as A


def cam():
    # looking straight down from 1 m above the origin (optical z = -world z)
    R = np.array([[1.0, 0, 0], [0, -1.0, 0], [0, 0, -1.0]])
    return Cam("c", 100, 80, 100.0, 100.0, 50.0, 40.0, R, np.array([0.0, 0.0, 1.0]))


def test_kappa_rule():
    assert A.kappa("grasp", False, 0.2) == A.KAPPA_NEAR
    assert A.kappa("above", True, 0.2) == A.KAPPA_CARRY
    assert A.kappa("above", False, 0.2) == A.KAPPA_FAR
    assert A.kappa("above", True, 0.01) == A.KAPPA_NEAR


def test_project_mask_hits_the_point_and_overlay_tints():
    m = A.project_mask(cam(), np.array([[0.0, 0.0, 0.0]]), r_px=1)
    assert m[40, 50] and m.sum() == 9
    img = np.zeros((80, 100, 3), np.uint8)
    o = A.overlay(img, m)
    assert o[40, 50, 0] > 0 and o[0, 0, 0] == 0


def test_region_points_on_a_box_in_depth():
    c = cam()
    depth = np.full((80, 100), 1.0)  # table plane z = 0
    depth[30:50, 40:60] = 0.9  # a 10 cm high box
    pts = A.region_points(c, depth, 0.0, [500, 500])
    assert pts is not None and np.allclose(pts[:, 2], 0.1, atol=1e-6)
    m = A.project_mask(c, pts, r_px=0)
    assert m[30:50, 40:60].mean() > 0.9 and m.sum() <= 400


def test_continuation_and_report():
    assert np.allclose(A.continuation("close", True, [0, 0, 1]), [0, 0, 1 + A.LIFT_START_M])
    assert A.continuation("close", False, [0, 0, 1]) is None
    t = A.report_text(0.9, True, ["cmd_mismatch"])
    assert "touches" in t and "grasp holds" in t and "cmd mismatch" in t
