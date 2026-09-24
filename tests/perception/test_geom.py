import math

import numpy as np
import pytest

from harvest.perception.geom import (Intr, backproject, cam_pose, intr_of, median_centroid, project, quat_to_R,
                                     to_table)


def _q_axis(axis, ang):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    return np.array([math.cos(ang / 2), *(a * math.sin(ang / 2))])


def test_quat_to_R_identity_and_z90():
    assert np.allclose(quat_to_R([1, 0, 0, 0]), np.eye(3))
    R = quat_to_R(_q_axis([0, 0, 1], math.pi / 2))
    assert np.allclose(R @ [1, 0, 0], [0, 1, 0])


def test_cam_pose_composes_link_and_mount():
    link_p, link_q = np.array([1.0, 2.0, 3.0]), _q_axis([0, 0, 1], math.pi / 2)
    mount = [0.1, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    p, R = cam_pose(link_p, link_q, mount)
    assert np.allclose(p, [1.0, 2.1, 3.0])  # mount x offset rotated by the link yaw
    assert np.allclose(R, quat_to_R(link_q))


def test_intr_from_spec():
    k = intr_of({"fx": 367.0, "fy": 367.0, "cx": 336.0, "cy": 188.0, "width": 672, "height": 376})
    assert k == Intr(367.0, 367.0, 336.0, 188.0, 672, 376)


def test_project_backproject_roundtrip_world_convention():
    # camera at origin looking +X (Isaac "world" convention: +X forward, +Y left, +Z up)
    K = Intr(100.0, 100.0, 50.0, 40.0, 100, 80)
    p, R = np.zeros(3), np.eye(3)
    P = np.array([[1.0, 0.0, 0.0], [2.0, 0.2, -0.1]])
    u, v, d = project(P, K, p, R)
    assert np.allclose(d, [1.0, 2.0])
    assert np.allclose(u, [50.0, 50.0 - 100 * 0.2 / 2.0])  # +Y (left) -> smaller u
    assert np.allclose(v, [40.0, 40.0 + 100 * 0.1 / 2.0])  # -Z (down) -> larger v
    # render a depth image of a plane at x = 2 and back-project a mask
    depth = np.full((80, 100), 2.0, np.float32)
    mask = np.zeros((80, 100), bool)
    mask[30:50, 40:60] = True
    pts = backproject(mask, depth, K, p, R)
    assert pts.shape == (400, 3) and np.allclose(pts[:, 0], 2.0)
    c = median_centroid(pts)
    # pixel centres (col + 0.5): mean u = 50 -> y = 0; mean v = 40 -> z = 0
    assert c == pytest.approx([2.0, 0.0, 0.0], abs=1e-9)


def test_backproject_drops_invalid_depth_and_range():
    K = Intr(100.0, 100.0, 50.0, 40.0, 100, 80)
    depth = np.full((80, 100), 1.0, np.float32)
    depth[0, 0], depth[0, 1], depth[0, 2] = np.inf, np.nan, 0.0
    mask = np.zeros((80, 100), bool)
    mask[0, :4] = True
    pts = backproject(mask, depth, K, np.zeros(3), np.eye(3), dmin=0.05, dmax=10.0)
    assert len(pts) == 1


def test_rotated_camera_roundtrip():
    K = Intr(200.0, 200.0, 100.0, 60.0, 200, 120)
    p = np.array([0.1, -0.2, 1.3])
    R = quat_to_R(_q_axis([0, 1, 0], 0.7))  # pitched down
    P = np.array([[0.5, -0.1, 0.9], [0.45, -0.25, 0.86]])
    u, v, d = project(P, K, p, R)
    depth = np.zeros((120, 200), np.float32)
    mask = np.zeros((120, 200), bool)
    for ui, vi, di in zip(u, v, d):
        c, r = int(ui), int(vi)
        depth[r, c] = di
        mask[r, c] = True
    back = backproject(mask, depth, K, p, R)
    # pixel quantisation (centre of the pixel) -> sub-cm error
    for q in back:
        assert np.min(np.linalg.norm(P - q, axis=1)) < 0.006


def test_median_centroid_min_points_and_table():
    assert median_centroid(np.zeros((3, 3)), min_pts=5) is None
    assert np.allclose(to_table([0.4, -0.1, 0.9], 0.85), [0.4, -0.1, 0.05])
