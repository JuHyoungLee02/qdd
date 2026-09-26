"""tools/xemb/geom.py: quaternion conventions, camera projection, GL->CV flip, depth back-projection, plane fit,
approach axis estimation (pure numpy)."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import geom as G  # noqa: E402


def test_quat_orders_agree_on_the_same_rotation():
    # 90 deg about z: wxyz (c, 0, 0, s), xyzw (0, 0, s, c)
    c, s = np.cos(np.pi / 4), np.sin(np.pi / 4)
    Rw = G.quat_wxyz_to_mat([c, 0, 0, s])
    Rx = G.quat_xyzw_to_mat([0, 0, s, c])
    assert np.allclose(Rw, Rx)
    assert np.allclose(Rw @ [1, 0, 0], [0, 1, 0], atol=1e-9)


def test_quat_is_normalised_before_use():
    assert np.allclose(G.quat_wxyz_to_mat([2, 0, 0, 0]), np.eye(3))


def test_pose_compose_and_inverse_roundtrip():
    T = G.pose_to_T([0.1, -0.2, 0.3], G.quat_wxyz_to_mat([0.9, 0.1, -0.3, 0.2]))
    assert np.allclose(G.inv_T(T) @ T, np.eye(4), atol=1e-9)
    p = np.array([0.4, 0.5, -0.6])
    assert np.allclose(G.apply_T(G.inv_T(T), G.apply_T(T, p)), p)


def test_projection_of_point_on_optical_axis_hits_principal_point():
    K = np.array([[500.0, 0, 320], [0, 500, 240], [0, 0, 1]])
    uv, z = G.project(K, np.eye(4), [0, 0, 2.0])
    assert np.allclose(uv, [320, 240]) and z == pytest.approx(2.0)


def test_projection_behind_camera_is_flagged():
    K = np.array([[500.0, 0, 320], [0, 500, 240], [0, 0, 1]])
    uv, z = G.project(K, np.eye(4), [0, 0, -1.0])
    assert z < 0


def test_gl_cam2world_to_cv_world2cam():
    # OpenGL camera looks along -z with y up; CV looks along +z with y down.
    C_gl = np.eye(4)
    C_gl[:3, 3] = [0, 0, 5]  # camera at z = 5, looking down -z (toward the origin)
    E = G.world2cam_cv_from_cam2world_gl(C_gl)
    uv, z = G.project(np.array([[100.0, 0, 50], [0, 100, 50], [0, 0, 1]]), E, [0, 0, 0])
    assert z == pytest.approx(5.0) and np.allclose(uv, [50, 50])
    uv2, _ = G.project(np.array([[100.0, 0, 50], [0, 100, 50], [0, 0, 1]]), E, [0, 1, 0])  # world +y is image up
    assert uv2[1] < 50


def test_rescale_intrinsics_square_pixels_vertical_fov():
    # MolmoBot: K stored for 480x480, video 1024x576 rendered with the same vertical fov
    K = np.array([[91.0, 0, 240], [0, 91.0, 240], [0, 0, 1]])
    K2 = G.rescale_K_vertical_fov(K, 1024, 576)
    assert K2[1, 1] == pytest.approx(91.0 * 576 / 480)
    assert K2[0, 0] == pytest.approx(K2[1, 1])
    assert K2[0, 2] == pytest.approx(512) and K2[1, 2] == pytest.approx(288)


def test_backproject_mask_centroid_recovers_a_plane_patch():
    K = np.array([[100.0, 0, 50], [0, 100, 50], [0, 0, 1]])
    depth = np.full((100, 100), 2.0)
    mask = np.zeros((100, 100), bool)
    mask[40:61, 40:61] = True  # centred on the principal point
    pts = G.backproject(K, depth, mask)
    assert pts.shape[1] == 3
    assert np.allclose(pts.mean(0), [0, 0, 2.0], atol=1e-6)


def test_backproject_skips_invalid_depth():
    K = np.array([[100.0, 0, 50], [0, 100, 50], [0, 0, 1]])
    depth = np.full((100, 100), 2.0)
    depth[0:50] = 0.0
    mask = np.ones((100, 100), bool)
    pts = G.backproject(K, depth, mask, dmin=0.05, dmax=9.0)
    assert len(pts) == 50 * 100


def test_plane_fit_recovers_normal_and_offset():
    rng = np.random.default_rng(0)
    xy = rng.uniform(-1, 1, (500, 2))
    pts = np.c_[xy, 0.85 + 0.0005 * rng.normal(size=500)]
    n, d, inl = G.fit_plane(pts, rng=rng)
    assert abs(abs(n[2]) - 1) < 1e-3
    assert abs(abs(d) - 0.85) < 2e-3
    assert inl > 0.95


def test_tilt_from_down():
    assert G.tilt_deg([0, 0, -1]) == pytest.approx(0.0)
    assert G.tilt_deg([1, 0, 0]) == pytest.approx(90.0)
    assert G.tilt_deg([0, 0, 1]) == pytest.approx(180.0)


def test_approach_axis_picks_the_local_axis_that_points_to_the_object():
    rng = np.random.default_rng(1)
    Rs, vs = [], []
    for _ in range(20):
        # random rotation; the true approach axis is local -y
        q = rng.normal(size=4)
        R = G.quat_wxyz_to_mat(q)
        Rs.append(R)
        vs.append(R @ np.array([0, -1.0, 0]) * 0.05 + rng.normal(0, 0.002, 3))
    axis, sign, score = G.approach_axis(Rs, vs)
    assert (axis, sign) == (1, -1) and score > 0.9
