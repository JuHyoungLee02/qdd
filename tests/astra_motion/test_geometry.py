"""E-Astra-motion coordinate frames: projection, ray-plane lift, two-view triangulation, depth lift (round trips)
and calibration-noise sensitivity. Written before harvest/astra_motion/geometry.py."""
import math

import numpy as np
import pytest

from harvest.astra_motion import geometry as G

TZ = 0.85


def look_at(pos, target, name="head", W=672, H=376, fx=367.0):
    """Camera (OpenCV optical: x right, y down, z forward) at pos looking at target, world z up."""
    z = np.asarray(target, float) - np.asarray(pos, float)
    z /= np.linalg.norm(z)
    x = np.cross(z, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.stack([x, y, z], axis=1)  # columns = camera axes in the base frame
    return G.Cam(name=name, W=W, H=H, fx=fx, fy=fx, cx=W / 2, cy=H / 2, R=R, t=np.asarray(pos, float))


HEAD = look_at((0.08, 0.02, 1.55), (0.45, -0.15, TZ))
WRIST = look_at((0.36, -0.28, TZ + 0.30), (0.42, -0.20, TZ), name="wrist", W=424, H=240, fx=223.4)


def test_quat_to_R_identity_and_yaw():
    assert np.allclose(G.quat_to_R((1, 0, 0, 0)), np.eye(3))
    R = G.quat_to_R((math.cos(math.pi / 4), 0, 0, math.sin(math.pi / 4)))  # yaw 90 deg
    assert np.allclose(R @ [1, 0, 0], [0, 1, 0], atol=1e-12)


def test_quat_rotvec_mul_and_yaw():
    q0 = (math.cos(math.pi / 4), 0, 0, math.sin(math.pi / 4))  # yaw 90 deg (the top-down grasp yaw)
    q = G.quat_mul(G.quat_from_rotvec((0, 0, 0.3)), q0)
    assert abs(G.yaw_between(q, q0) - 0.3) < 1e-9
    assert np.allclose(G.quat_from_rotvec((0, 0, 0)), (1, 0, 0, 0))
    assert np.allclose(G.quat_to_R(G.quat_from_rotvec((0.2, -0.1, 0.3))) @ G.quat_to_R(
        G.quat_from_rotvec((-0.2, 0.1, -0.3))), np.eye(3), atol=1e-12)


def test_project_centre_pixel():
    p = HEAD.t + HEAD.R[:, 2] * 0.7  # on the optical axis
    u, v, z = G.project(HEAD, p)
    assert abs(u - HEAD.cx) < 1e-9 and abs(v - HEAD.cy) < 1e-9 and abs(z - 0.7) < 1e-12


def test_pixel_index_convention():
    """Integer pixel index i has its centre at continuous coordinate i + 0.5 (image plane spans [0, W])."""
    o, d = G.pixel_ray(HEAD, HEAD.cx - 0.5, HEAD.cy - 0.5)
    assert np.allclose(d, HEAD.R[:, 2])


@pytest.mark.parametrize("p", [(0.40, -0.20, TZ), (0.45, -0.05, TZ + 0.095), (0.38, -0.33, TZ + 0.20)])
def test_plane_lift_round_trip(p):
    p = np.array(p)
    u, v, _ = G.project(HEAD, p)
    q = G.lift_plane(HEAD, u - G.PIX_C, v - G.PIX_C, p[2])
    assert np.linalg.norm(q - p) < 1e-9


def test_plane_lift_behind_or_parallel_is_none():
    # a plane above the camera: the ray (looking down) never reaches it in front of the camera
    u, v, _ = G.project(HEAD, (0.40, -0.20, TZ))
    assert G.lift_plane(HEAD, u, v, 2.5) is None


@pytest.mark.parametrize("p", [(0.40, -0.20, TZ + 0.0475), (0.44, -0.12, TZ + 0.10), (0.37, -0.30, TZ + 0.015)])
def test_triangulate_round_trip(p):
    p = np.array(p)
    uh, vh, _ = G.project(HEAD, p)
    uw, vw, _ = G.project(WRIST, p)
    q, gap = G.triangulate(HEAD, (uh - G.PIX_C, vh - G.PIX_C), WRIST, (uw - G.PIX_C, vw - G.PIX_C))
    assert np.linalg.norm(q - p) < 1e-9 and gap < 1e-9


def test_triangulate_reports_gap_for_inconsistent_points():
    a, b = np.array([0.40, -0.20, TZ]), np.array([0.46, -0.10, TZ + 0.05])
    uh, vh, _ = G.project(HEAD, a)
    uw, vw, _ = G.project(WRIST, b)
    _, gap = G.triangulate(HEAD, (uh - G.PIX_C, vh - G.PIX_C), WRIST, (uw - G.PIX_C, vw - G.PIX_C))
    assert gap > 0.01


def test_depth_lift_round_trip():
    """pixel + depth -> base -> pixel, with a synthetic z-depth map of the table plane."""
    depth = G.plane_depth_map(HEAD, TZ)
    for (iu, iv) in [(100, 300), (336, 250), (600, 360)]:
        q = G.lift_depth(HEAD, iu, iv, depth)
        assert abs(q[2] - TZ) < 1e-9
        u, v, _ = G.project(HEAD, q)
        assert abs(u - (iu + G.PIX_C)) < 1e-6 and abs(v - (iv + G.PIX_C)) < 1e-6


def test_depth_lift_invalid_pixel_uses_window_median():
    depth = G.plane_depth_map(HEAD, TZ)
    depth[250, 336] = np.inf
    q = G.lift_depth(HEAD, 336, 250, depth)
    assert q is not None and abs(q[2] - TZ) < 0.003


def test_pixel_of_inside_and_outside():
    u, v, _ = G.project(HEAD, (0.40, -0.20, TZ))
    iu, iv, inside = G.pixel_of(HEAD, (0.40, -0.20, TZ))
    assert inside and iu == int(math.floor(u)) and iv == int(math.floor(v))
    assert not G.pixel_of(HEAD, (0.40, -0.20, 3.0))[2]  # behind / off image


def test_cam_json_round_trip():
    c = G.Cam.from_json(HEAD.to_json())
    assert c.name == HEAD.name and np.allclose(c.R, HEAD.R) and np.allclose(c.t, HEAD.t) and c.fx == HEAD.fx


def test_rotate_cam_small_angle():
    c = G.rotate_cam(HEAD, axis=(1, 0, 0), deg=0.5)
    ang = math.degrees(math.acos(np.clip((np.trace(c.R.T @ HEAD.R) - 1) / 2, -1, 1)))
    assert abs(ang - 0.5) < 1e-6


def test_sensitivity_plane_lift_scales_with_rotation_noise():
    """0.5 deg extrinsic rotation error moves a plane-lifted table point by about range * angle / sin(elevation):
    bounded (here < 15 mm at ~0.9 m range), and larger than for 0.1 deg."""
    p = np.array([0.42, -0.18, TZ])
    e = {}
    for deg in (0.1, 0.5):
        errs = []
        for ax in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            c = G.rotate_cam(HEAD, ax, deg)
            u, v, _ = G.project(HEAD, p)  # the pixel the true camera saw
            errs.append(np.linalg.norm(G.lift_plane(c, u - G.PIX_C, v - G.PIX_C, TZ) - p))
        e[deg] = max(errs)
    assert e[0.1] < e[0.5] < 0.015


def test_sensitivity_report_keys():
    r = G.sensitivity(HEAD, WRIST, np.array([0.42, -0.18, TZ + 0.0475]), rot_deg=0.5, pix=2.0, plane_dz=0.005,
                      n=50, seed=0)
    for k in ("plane_rot_mm", "plane_pix_mm", "plane_h_mm", "tri_rot_mm", "tri_pix_mm"):
        assert k in r and r[k] >= 0.0
    assert r["plane_h_mm"] > 0
