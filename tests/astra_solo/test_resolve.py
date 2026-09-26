"""Point-then-act resolver (canon §97 보충 2): a pointed pixel + the head z-depth -> the object's footprint centre and top,
then the height intent -> TCP target. Scene = the fake world's ray-cast table and boxes (exact depth)."""
import numpy as np

from harvest.astra_motion import geometry as G
from harvest.astra_solo import resolve as RS

from astra_motion.fakeworld import HEAD, TZ, raycast
from harvest.sim.scene import OBJ_GEOM

MUG = np.array([0.43, -0.30, TZ + 0.095 / 2])
TRAY = np.array([0.47, -0.10, TZ + 0.015 / 2])


def _scene():
    boxes = []
    for k, c in (("o3", MUG), ("o5", TRAY)):
        he = np.array(OBJ_GEOM[k]["half_extents"])
        boxes.append((c - he, c + he))
    return raycast(HEAD, boxes)[1]


def _pt(p):
    u, v, _ = G.project(HEAD, p)
    return RS.to_scaled(u, v, HEAD.W, HEAD.H)


def test_scale_roundtrip():
    for u, v in ((0.5, 0.5), (335.5, 200.5), (671.5, 375.5)):
        iu, iv = RS.to_pixel(RS.to_scaled(u, v, 672, 376), 672, 376)
        assert abs(iu + 0.5 - u) <= 1 and abs(iv + 0.5 - v) <= 1
    assert RS.to_pixel([1000, 1000], 672, 376) == (671, 375)  # clamped inside
    assert RS.to_pixel([0, 0], 672, 376) == (0, 0)


def test_point_on_body_gives_footprint_centre_and_top():
    d = _scene()
    for p in (MUG, MUG + [0, 0, 0.04], MUG + [-0.02, 0.01, 0.0475]):  # body middle, near the top, on the top face
        r = RS.resolve_point(HEAD, d, TZ, _pt(p))
        assert r["kind"] == "object" and not r["snapped"]
        assert np.hypot(r["xy"][0] - MUG[0], r["xy"][1] - MUG[1]) < 0.006, r
        assert abs(r["top"] - (TZ + 0.095)) < 0.003
        assert abs(r["plane"] - TZ) < 1e-6


def test_tray_and_table_and_snap():
    d = _scene()
    r = RS.resolve_point(HEAD, d, TZ + 0.01, _pt(TRAY + [0, 0, 0.0075]))  # prior off by 1 cm: plane is measured
    assert r["kind"] == "object" and abs(r["top"] - (TZ + 0.015)) < 0.002 and abs(r["plane"] - TZ) < 1e-6
    assert np.hypot(r["xy"][0] - TRAY[0], r["xy"][1] - TRAY[1]) < 0.02
    q = np.array([0.35, -0.45, TZ])  # bare table
    r = RS.resolve_point(HEAD, d, TZ, _pt(q))
    assert r["kind"] == "table" and np.hypot(r["xy"][0] - q[0], r["xy"][1] - q[1]) < 0.003
    side = MUG + [0.0, 0.032 + 0.006, -0.03]  # 6 mm beside the mug's +y face: a few px off the silhouette
    r = RS.resolve_point(HEAD, d, TZ, _pt(side))
    assert r["kind"] == "object" and r["snapped"] and np.hypot(r["xy"][0] - MUG[0], r["xy"][1] - MUG[1]) < 0.006


def test_intents():
    res = {"xy": [0.4, -0.3], "top": TZ + 0.095}
    tcp = [0.3, -0.2, TZ + 0.3]
    p, n = RS.target_of("above", res, TZ, tcp, holding=False, grip_offset=None)
    assert np.allclose(p, [0.4, -0.3, TZ + 0.175]) and n == []
    p, _ = RS.target_of("grasp", res, TZ, tcp, False, None)
    assert np.isclose(p[2], TZ + 0.075)
    tray = {"xy": [0.47, -0.1], "top": TZ + 0.015}
    p, n = RS.target_of("place", tray, TZ, tcp, True, 0.075)
    assert np.isclose(p[2], TZ + 0.015 + 0.075 + 0.01) and n == []
    p, n = RS.target_of("above", tray, TZ, tcp, True, 0.075)
    assert np.isclose(p[2], TZ + 0.015 + 0.08 + 0.075)
    p, n = RS.target_of("place", tray, TZ, tcp, True, None)
    assert n == ["grip_offset_unknown"] and np.isclose(p[2], TZ + 0.015 + RS.PLACE_FALLBACK_M)
    p, n = RS.target_of("lift", None, TZ, tcp, True, 0.075)
    assert np.allclose(p, [0.3, -0.2, TZ + 0.22])
