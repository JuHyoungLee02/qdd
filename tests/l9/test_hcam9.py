import math

import numpy as np
import pytest

from harvest.l9 import hcam9 as HC

M = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])  # world_isaac.WORLD_CONV_TO_OPTICAL


def test_fov_fx_roundtrip_and_std():
    assert HC.fx_from_hfov(HC.STD_HFOV) == pytest.approx(367.0)
    assert HC.fx_from_hfov(69.0) == pytest.approx(489.3, abs=0.5)
    for h in (55.0, 69.0, 85.0, 105.0):
        assert HC.hfov_from_fx(HC.fx_from_hfov(h)) == pytest.approx(h)
    K = HC.K_of(85.0)
    assert K[0, 2] == 336.0 and K[1, 2] == 188.0 and K[0, 0] == K[1, 1]


def test_look_and_pitch_pan():
    for p, a in ((45.0, 0.0), (30.0, -20.0), (62.0, 15.0)):
        R = HC.look_R(p, a)
        assert np.allclose(R.T @ R, np.eye(3))
        assert HC.pitch_pan(R) == pytest.approx((p, a))
        assert R[2, 1] == pytest.approx(0.0, abs=1e-12)  # no roll: camera +Y stays horizontal


def test_repitch_keeps_heading_and_position_math():
    R0 = HC.look_R(40.0, 17.0)
    R1 = HC.repitch(R0, 58.0)
    assert HC.pitch_pan(R1) == pytest.approx((58.0, 17.0))
    R, t = HC.ffw_pose(R0, (0.1, 0.0, 1.3), {"dz": -0.1, "pitch": 33.0})
    assert t[2] == pytest.approx(1.2) and HC.pitch_pan(R)[0] == pytest.approx(33.0)
    R, t = HC.ffw_pose(R0, (0.1, 0.0, 1.3), HC.std_ffw())
    assert np.allclose(R, R0) and t[2] == pytest.approx(1.3)


def test_quat_roundtrip_and_mount():
    rng = np.random.default_rng(0)
    for _ in range(20):
        q = rng.normal(size=4)
        q = q / np.linalg.norm(q)
        R = HC.quat_to_R(q)
        assert np.allclose(HC.quat_to_R(HC.R_to_quat(R)), R)
    qp = HC.R_to_quat(HC.axis_angle_R((0.3, 0.2, 0.9), 0.7))
    pp = np.array([0.2, -0.1, 1.2])
    Rc, tc = HC.look_R(50.0, -8.0), np.array([0.3, 0.05, 1.4])
    pos, q = HC.mount_of(pp, qp, tc, Rc)
    Rp = HC.quat_to_R(qp)
    assert np.allclose(pp + Rp @ np.asarray(pos), tc)
    assert np.allclose(Rp @ HC.quat_to_R(q), Rc)


def test_coin_is_half_and_stable():
    c = [HC.coin(s) for s in range(4000)]
    assert 0.46 < c.count("rand") / len(c) < 0.54
    assert HC.coin(123) == HC.coin(123)


def test_draw_ffw_inside_band():
    for s in range(300):
        h0 = 0.42 + (s % 27) / 100.0
        d = HC.draw_ffw(s, h0)
        assert HC.H_RANGE[0] - 1e-9 <= h0 + d["dz"] <= HC.H_RANGE[1] + 1e-9 and abs(d["dz"]) <= HC.DZ_MAX + 1e-9
        assert HC.PITCH_RANGE[0] <= d["pitch"] <= HC.PITCH_RANGE[1]
        assert HC.HFOV_RANGE[0] <= d["hfov"] <= HC.HFOV_RANGE[1]
    assert HC.draw_ffw(5, 0.5) == HC.draw_ffw(5, 0.5) != HC.draw_ffw(5, 0.5, 1)


def test_draw_hold_exactly_one_axis_out():
    axes = set()
    for s in range(300):
        h0 = 0.5
        d = HC.draw_hold_ffw(s, h0)
        h = h0 + d["dz"]
        out = {"height": not (HC.H_RANGE[0] <= h <= HC.H_RANGE[1]),
               "pitch": not (HC.PITCH_RANGE[0] <= d["pitch"] <= HC.PITCH_RANGE[1]),
               "hfov": not (HC.HFOV_RANGE[0] <= d["hfov"] <= HC.HFOV_RANGE[1])}
        assert sum(out.values()) == 1 and out[d["axis"]]
        axes.add(d["axis"])
    assert axes == {"height", "pitch", "hfov"}


def test_mast_draw_and_pose():
    for s in range(100):
        d = HC.draw_mast(s)
        for k, (lo, hi) in HC.MAST_RANGE.items():
            assert lo <= d[k] <= hi
        assert d["hfov"] == HC.D435_HFOV
    d = HC.draw_mast(0, default=True)
    R, t = HC.mast_pose((0.0, -0.23, 0.80), 0.85, d)
    assert t == pytest.approx((0.0, -0.71, 2.00))
    assert HC.pitch_pan(R) == pytest.approx((68.0, 30.0))
    r = HC.realized(R, t, 0.85)
    assert r["height_above_surface_m"] == pytest.approx(1.15) and r["height_floor_m"] == pytest.approx(2.00)


def test_camera_line_from_cams_json():
    Rwc = HC.look_R(45.0, -2.0)
    cam = {"W": 672, "H": 376, "fx": 367.0, "fy": 367.0, "cx": 336.0, "cy": 188.0,
           "R": (Rwc @ M).tolist(), "t": [0.05, 0.0, 1.34]}
    s = HC.line(cam, "l9/ffw_sg2")
    assert s == ("camera: head, 672x376 px, fx 367 fy 367 cx 336 cy 188, 1.34 m above the floor, "
                 "pitch 45 deg down, pan -2 deg; source: l9/ffw_sg2")
