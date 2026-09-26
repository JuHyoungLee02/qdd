"""L8X-assets: support-surface extraction from triangle meshes (pure numpy, no Isaac)."""
import numpy as np
import pytest

from harvest.sim.assets_x import surfaces as S


def box_mesh(lo, hi):
    """Closed axis-aligned box as (points, faces) with outward normals."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = np.array([[0, 2, 1], [0, 3, 2],  # bottom (down)
                  [4, 5, 6], [4, 6, 7],  # top (up)
                  [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    return P, F


def merge(*meshes):
    Ps, Fs, n = [], [], 0
    for P, F in meshes:
        Ps.append(P)
        Fs.append(F + n)
        n += len(P)
    return np.concatenate(Ps), np.concatenate(Fs)


def test_single_table_top():
    P, F = box_mesh((0, 0, 0.81), (0.6, 1.0, 0.85))
    out = S.mesh_support_surfaces(P, F)
    assert len(out) == 1
    s = out[0]
    assert s["top_z"] == pytest.approx(0.85, abs=1e-6)
    (x0, x1), (y0, y1) = s["free_box"]
    assert x0 == pytest.approx(0.0, abs=0.011) and x1 == pytest.approx(0.6, abs=0.011)
    assert y0 == pytest.approx(0.0, abs=0.011) and y1 == pytest.approx(1.0, abs=0.011)
    assert s["covered_above"] is None
    assert s["area"] == pytest.approx(0.6, rel=0.02)


def test_shelf_tiers_are_covered_by_next_tier():
    tiers = [box_mesh((0, 0, z - 0.02), (0.4, 0.8, z)) for z in (0.40, 0.75, 1.10)]
    sides = [box_mesh((0, -0.02, 0), (0.4, 0.0, 1.12)), box_mesh((0, 0.8, 0), (0.4, 0.82, 1.12))]
    P, F = merge(*tiers, *sides)
    out = S.mesh_support_surfaces(P, F, min_area=0.02)
    tops = sorted(round(s["top_z"], 3) for s in out)
    assert tops == [0.40, 0.75, 1.10]
    by = {round(s["top_z"], 2): s for s in out}
    assert by[0.4]["covered_above"] == pytest.approx(0.73, abs=1e-6)  # underside of the 0.75 tier
    assert by[0.75]["covered_above"] == pytest.approx(1.08, abs=1e-6)
    assert by[1.1]["covered_above"] is None


def test_bin_floor_is_container_with_rim():
    floor = box_mesh((0, 0, 0.0), (0.30, 0.20, 0.01))
    walls = [box_mesh((0, 0, 0), (0.30, 0.01, 0.12)), box_mesh((0, 0.19, 0), (0.30, 0.20, 0.12)),
             box_mesh((0, 0, 0), (0.01, 0.20, 0.12)), box_mesh((0.29, 0, 0), (0.30, 0.20, 0.12))]
    P, F = merge(floor, *walls)
    out = S.mesh_support_surfaces(P, F, min_area=0.01)
    inner = [s for s in out if abs(s["top_z"] - 0.01) < 1e-6]
    assert len(inner) == 1
    s = inner[0]
    assert s["container"] is True
    assert s["rim_z"] == pytest.approx(0.12, abs=1e-6)
    (x0, x1), (y0, y1) = s["free_box"]
    assert x0 >= 0.0095 and x1 <= 0.2905 and y0 >= 0.0095 and y1 <= 0.1905


def test_hole_shrinks_free_box():
    # an L-shaped top: 0.6 x 1.0 minus the corner x > 0.3 and y > 0.5 (as two boxes of the same height)
    a = box_mesh((0, 0, 0.8), (0.6, 0.5, 0.85))
    b = box_mesh((0, 0.5, 0.8), (0.3, 1.0, 0.85))
    P, F = merge(a, b)
    s = S.mesh_support_surfaces(P, F)[0]
    (x0, x1), (y0, y1) = s["free_box"]
    area = (x1 - x0) * (y1 - y0)
    assert area == pytest.approx(0.30, abs=0.02)  # the largest full rectangle (0.6 x 0.5 or 0.3 x 1.0)


def test_small_or_tilted_faces_are_ignored():
    P, F = box_mesh((0, 0, 0.0), (0.05, 0.05, 0.9))  # a pole: top 5 x 5 cm is below min_side
    assert S.mesh_support_surfaces(P, F) == []
    P = np.array([[0, 0, 0.8], [1, 0, 1.2], [1, 1, 1.2], [0, 1, 0.8]], float)  # 22 deg ramp
    F = np.array([[0, 1, 2], [0, 2, 3]])
    assert S.mesh_support_surfaces(P, F) == []


def test_counter_under_wall_cabinet_splits_open_and_covered():
    top = box_mesh((0, 0, 0), (0.6, 1.0, 0.9))
    cab = box_mesh((0.3, 0, 1.35), (0.6, 1.0, 1.9))
    out = S.mesh_support_surfaces(*merge(top, cab))
    at = [s for s in out if abs(s["top_z"] - 0.9) < 1e-6]
    assert len(at) == 2
    op = next(s for s in at if s["covered_above"] is None)
    cv = next(s for s in at if s["covered_above"] is not None)
    assert op["free_box"][0] == pytest.approx([0.0, 0.3], abs=0.011)
    assert cv["free_box"][0] == pytest.approx([0.3, 0.6], abs=0.011)
    assert cv["clearance"] == pytest.approx(0.45, abs=1e-6)


def test_transform_applies_scale_and_yaw():
    P, F = box_mesh((-0.3, -0.5, 0.0), (0.3, 0.5, 0.85))
    s = S.mesh_support_surfaces(P, F)[0]
    t = S.transform_surface(s, pos=(0.6, -0.1, 0.02), yaw=np.pi / 2)
    assert t["top_z"] == pytest.approx(0.87, abs=1e-6)
    (x0, x1), (y0, y1) = t["xy_box"]
    assert (x1 - x0) == pytest.approx(1.0, abs=0.03) and (y1 - y0) == pytest.approx(0.6, abs=0.03)
    assert (x0 + x1) / 2 == pytest.approx(0.6, abs=0.011) and (y0 + y1) / 2 == pytest.approx(-0.1, abs=0.011)
    with pytest.raises(ValueError):
        S.transform_surface(s, pos=(0, 0, 0), yaw=0.3)  # only multiples of 90 deg keep a box a box


def test_rotated_collider_boxes_give_the_same_top():
    from harvest.sim.assets_x import usd_import as U
    lo, hi = np.array([-0.3, -0.2, 0.0]), np.array([0.3, 0.2, 0.75])
    C = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    th = np.pi / 2
    Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    P, F = U.boxes_mesh([("a", C @ Rz.T)])
    s = S.mesh_support_surfaces(P, F)
    assert len(s) == 1 and s[0]["top_z"] == pytest.approx(0.75)
    (x0, x1), (y0, y1) = s[0]["free_box"]
    assert x1 - x0 == pytest.approx(0.4, abs=0.011) and y1 - y0 == pytest.approx(0.6, abs=0.011)
