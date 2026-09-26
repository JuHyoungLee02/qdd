"""tools/mar2/mar2_lib.py -- MolmoAct trace label semantics and the geometry used by the readiness gates."""
import colorsys
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "mar2"))
import mar2_lib as L  # noqa: E402


def test_subsample_matches_molmoact_semantics():
    pts = [[i, 2 * i] for i in range(11)]
    # np.linspace(0, 10, 5, dtype=int) = [0, 2, 5, 7, 10]: first (current) and last (episode end) included
    assert L.molmo_subsample(pts, 5) == [[0, 0], [2, 4], [5, 10], [7, 14], [10, 20]]
    assert L.molmo_subsample(pts[:4], 5) == pts[:4]          # m <= k: all points
    assert L.molmo_subsample([None, [1, 1], None], 5) == [[1, 1]]  # None dropped
    assert L.molmo_subsample([None, None], 5, fallback=[3, 3]) == [[3, 3]]
    assert L.molmo_subsample([None], 5) == []


def test_u255_round_trip_within_half_grid():
    W, H = 672, 376
    for u, v in [(0.5, 0.5), (336.0, 188.0), (671.5, 375.5), (100.3, 250.9)]:
        q = L.to_u255(u, v, W, H)
        assert all(0 <= c <= 255 for c in q)
        u2, v2 = L.from_u255(q, W, H)
        assert abs(u2 - u) <= 0.5 * (W - 1) / 255 + 1e-9
        assert abs(v2 - v) <= 0.5 * (H - 1) / 255 + 1e-9
    assert L.to_u255(-50, 1000, W, H) == [0, 255]  # clipped


def test_trace_labels_per_frame():
    W, H = 672, 376
    uv = np.array([[10.0 + 20 * i, 100.0] for i in range(12)])
    uv[3] = [-5.0, 100.0]  # outside the image -> dropped
    tr = L.trace_labels(uv, W, H)
    assert len(tr) == 12
    assert tr[0][0] == L.to_u255(10.0, 100.0, W, H) and len(tr[0]) == 5
    assert tr[0][-1] == L.to_u255(uv[-1][0], 100.0, W, H)
    assert tr[-1] == [L.to_u255(uv[-1][0], 100.0, W, H)]  # t = e: one point
    assert tr[3][0] == L.to_u255(uv[4][0], 100.0, W, H)  # current invalid: next valid future point first
    assert len(tr[9]) == 3  # e - t < 4: all remaining points


def test_raster_centroid_iou():
    poly = L.convex_hull([[10, 10], [20, 10], [20, 20], [10, 20], [15, 15]])
    m = L.raster_convex(poly, 40, 30)
    assert m.sum() == 100
    assert L.mask_centroid(m) == pytest.approx((15.0, 15.0))
    m2 = L.raster_convex(L.convex_hull([[15, 10], [25, 10], [25, 20], [15, 20]]), 40, 30)
    assert L.iou(m, m2) == pytest.approx(50 / 150)


def test_project_matches_perception_geom():
    geom = pytest.importorskip("harvest.perception.geom")
    K = {"fx": 367.0, "fy": 367.0, "cx": 336.0, "cy": 188.0}
    R = np.array([[0.7702197, 0.0, 0.6377787], [0.0, 1.0, 0.0], [-0.6377787, 0.0, 0.7702197]])
    p = np.array([0.105, 0.025, 1.405])
    P = np.array([[0.45, -0.1, 0.9], [0.5, 0.1, 0.87]])
    u, v, d = geom.project(P, geom.Intr(367.0, 367.0, 336.0, 188.0, 672, 376), p, R)
    out = L.project(P, K, p, R)
    assert np.allclose(out[:, 0], u) and np.allclose(out[:, 1], v) and np.allclose(out[:, 2], d)


def test_fit_offset_recovers_synthetic():
    rng = np.random.default_rng(0)
    n = 50
    p = rng.normal(size=(n, 3))
    A = rng.normal(size=(n, 3, 3))
    R = np.stack([np.linalg.qr(a)[0] for a in A])
    o, t = np.array([0.01, -0.02, 0.15]), np.array([0.3, -0.1, 0.9])
    tgt = L.apply_offset(p, R, o, t)
    o2, t2 = L.fit_offset(p, R, tgt)
    assert np.allclose(o2, o) and np.allclose(t2, t)


def test_dir8_sectors():
    assert L.dir8(1, 0) == "plus_x"
    assert L.dir8(1, 1) == "plus_x_plus_y"
    assert L.dir8(0, -1) == "minus_y"
    assert L.dir8(-1, 0.01) == "minus_x"
    assert L.dir8(1, -0.9) == "plus_x_minus_y"


def test_hsv_matches_colorsys():
    img = np.array([[[217, 0, 166], [204, 20, 20], [26, 64, 217], [26, 166, 51], [128, 128, 128]]], np.uint8)
    h, s, v = L.rgb_to_hsv(img)
    for i, (r, g, b) in enumerate(img[0]):
        hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        assert h[0, i] == pytest.approx(hh * 360 % 360, abs=1e-6)
        assert s[0, i] == pytest.approx(ss) and v[0, i] == pytest.approx(vv)
    # the four object colours fall in their own rule only
    names = ["o11", "o3", "o5", "o8"]
    for i, n in enumerate(names):
        for j, m in enumerate(names):
            assert bool(L.colour_mask(img[:, i:i + 1], m)[0, 0]) == (i == j)
    assert not any(L.colour_mask(img[:, 4:5], m)[0, 0] for m in names)
    assert not math.isnan(h[0, 0])
